#!/usr/bin/env python3
"""
MTFSS - Multi-Tenant Folder Sorting Sieve
A Python script that automatically organizes emails into folders based on recipient addresses.
"""

import argparse
import email
import email.message
import logging
import os
import re
import sys
import time
from imaplib import IMAP4, IMAP4_SSL
from typing import List, Optional, Tuple

ARCHIVE_FOLDER = "archived"


class MTFSSProcessor:
    """Main class for processing emails and organizing them into folders."""

    def __init__(self, imap_server: str, username: str, password: str, primary_domain: str):
        """
        Initialize the MTFSS processor.

        Args:
            imap_server: IMAP server hostname
            username: IMAP username
            password: IMAP password
            primary_domain: Primary domain for user folder routing
        """
        self.imap_server = imap_server
        self.username = username
        self.password = password
        self.primary_domain = primary_domain
        self.connection: Optional[IMAP4_SSL] = None
        self.first_pass = True

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """
        Establish connection to IMAP server.
        """
        try:
            self.logger.info("Connecting to IMAP server: %s", self.imap_server)
            self.logger.info("Using username: %s", self.username)
            self.logger.info("Using password: %s", '*' * len(self.password))
            self.logger.info("Using primary domain: %s", self.primary_domain)
            self.connection = IMAP4_SSL(self.imap_server)
            self.connection.login(self.username, self.password)
            self.logger.info("Connected to IMAP server: %s", self.imap_server)
            return True
        except IMAP4.error as e:
            self.logger.error("Failed to connect to IMAP server: %s", e)
            return False

    def disconnect(self):
        """Close IMAP connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                self.logger.info("Disconnected from IMAP server")
            except IMAP4.error as e:
                self.logger.error("Error disconnecting: %s", e)
                raise
            finally:
                self.connection = None

    def extract_recipients(self, msg: email.message.Message) -> List[str]:
        """
        Extract recipient addresses from email headers.

        Args:
            msg: Email message object

        Returns:
            List of recipient email addresses
        """
        recipients = []

        # Check To, CC, and BCC headers
        for header in ['To', 'Cc', 'Bcc']:
            header_value = msg.get(header)
            if header_value:
                # Extract email addresses using regex
                emails = re.findall(
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', header_value)
                recipients.extend(emails)

        return recipients

    def parse_email_address(self, email_addr: str) -> Tuple[str, str]:
        """
        Parse email address into user and domain parts.

        Args:
            email_addr: Email address to parse

        Returns:
            Tuple of (user, domain)
        """
        match = re.match(r'^([^@]+)@(.+)$', email_addr.strip())
        if match:
            return match.group(1), match.group(2)
        return "", ""

    def determine_folder(self, user: str, domain: str) -> str:
        """
        Determine the target folder for an email based on recipient.

        Args:
            user: User part of email address
            domain: Domain part of email address

        Returns:
            Target folder name
        """
        if not user or not domain:
            return "unmatched"

        user_folder = user.capitalize()
        domain_folder = domain.lower().replace('.', '_')

        # Check if this is an ignored user
        ignore_folder = f"{ARCHIVE_FOLDER}.{user_folder}"
        if self.folder_exists(ignore_folder):
            return ignore_folder

        # Route based on domain
        if domain == self.primary_domain:
            return f"Inbox.{user_folder}"

        return f"Inbox.{user_folder}@{domain_folder}"

    def folder_exists(self, folder_name: str) -> bool:
        """
        Check if a folder exists on the IMAP server.

        Args:
            folder_name: Name of folder to check

        Returns:
            True if folder exists, False otherwise
        """
        try:
            if not self.connection:
                raise ValueError("No IMAP connection available")

            # List folders matching the name
            status, folders = self.connection.list('""', folder_name)
            print(
                f"DEBUG: folder_exists('{folder_name}') returned status={status}, folders={folders}")
            return status == 'OK' and folders is not None and len(folders) > 0 and folders[0] is not None
        except IMAP4.error as e:
            self.logger.error("Error checking folder existence: %s", e)
            raise

    def create_folder(self, folder_name: str) -> bool:
        """
        Create a folder on the IMAP server.

        Args:
            folder_name: Name of folder to create

        Returns:
            True if folder created successfully, False otherwise
        """
        try:
            if not self.connection:
                return False

            status, _ = self.connection.create(folder_name)
            if status == 'OK':
                self.logger.info("Created folder: %s", folder_name)
                return True
            else:
                self.logger.error("Failed to create folder: %s", folder_name)
                return False
        except IMAP4.error as e:
            self.logger.error("Error creating folder %s: %s", folder_name, e)
            raise

    def move_email(self, msg_id: str, target_folder: str) -> bool:
        """
        Move an email to the target folder.

        Args:
            msg_id: Message ID to move
            target_folder: Destination folder

        Returns:
            True if moved successfully, False otherwise
        """
        try:
            if not self.connection:
                raise ValueError("No IMAP connection available")

            # Ensure target folder exists
            if not self.folder_exists(target_folder):
                self.create_folder(target_folder)

            # Move the message
            status, _ = self.connection.copy(msg_id, target_folder)
            if status == 'OK':
                self.logger.info("Moved message %s to %s",
                                 msg_id, target_folder)
                # Mark original message for deletion
                self.connection.store(msg_id, '+FLAGS', '\\Deleted')
                return True
            else:
                self.logger.error(
                    "Failed to move message %s to %s", msg_id, target_folder)
                return False
        except IMAP4.error as e:
            self.logger.error("Error moving message %s: %s", msg_id, e)
            raise

    def process_inbox(self):
        """Process all emails in the inbox and sort them into folders."""
        if not self.connection:
            self.logger.error("No IMAP connection available")
            return

        # Select inbox
        self.connection.select('INBOX')

        if not self.folder_exists(ARCHIVE_FOLDER):
            self.create_folder(ARCHIVE_FOLDER)

        # Search for all unread emails
        search_type = 'UNSEEN' if not self.first_pass else 'ALL'
        status, messages = self.connection.search(None, search_type)
        self.first_pass = False
        if status != 'OK':
            self.logger.error("Failed to search for messages")
            return

        message_ids = messages[0].split()
        self.logger.info("Processing %s new messages", len(message_ids))

        for msg_id in message_ids:
            try:
                # Fetch the email
                status, msg_data = self.connection.fetch(
                    msg_id, '(RFC822)')
                if status != 'OK':
                    self.logger.error("Failed to fetch message %s", msg_id)
                    continue

                # Parse email
                # pyright: ignore[reportOptionalSubscript]
                raw_email = msg_data[0][1]
                if not isinstance(raw_email, bytes):
                    self.logger.error(
                        "Invalid email data format for message %s", msg_id)
                    continue
                msg = email.message_from_bytes(raw_email)

                # Extract recipients
                recipients = self.extract_recipients(msg)

                if not recipients:
                    self.logger.warning(
                        "No recipients found for message %s", msg_id)
                    self.move_email(msg_id, "unmatched")
                    continue

                # Process first recipient (primary routing)
                recipient = recipients[0]
                user, domain = self.parse_email_address(recipient)
                target_folder = self.determine_folder(user, domain)

                # Move email to target folder
                self.move_email(msg_id, target_folder)

            except IMAP4.error as e:
                self.logger.error("Error processing message %s: %s", msg_id, e)
                continue

        # Expunge deleted messages
        self.connection.expunge()

    def run_continuous(self, check_interval: int = 30):
        """
        Run continuously, checking for new emails at regular intervals.

        Args:
            check_interval: Seconds between checks
        """
        self.logger.info(
            "Starting continuous monitoring (check every %ds)", check_interval)

        def try_connect():
            if not self.connection:
                if not self.connect():
                    self.logger.error("Failed to connect, waiting...")
                    return False
            return True

        while True:
            try:
                if try_connect():
                    self.process_inbox()

            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, shutting down...")
                break

            time.sleep(check_interval)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='MTFSS - Multi-Tenant Folder Sorting Sieve')
    parser.add_argument('-s', '--server', required=True,
                        help='IMAP server hostname')
    parser.add_argument('-u', '--username', required=True,
                        help='IMAP username')
    parser.add_argument('-p', '--password',
                        help='IMAP password (or set IMAP_PASSWORD env var)')
    parser.add_argument('-d', '--domain',
                        required=True,
                        help='Primary domain for user folder routing')
    parser.add_argument('-i', '--interval', type=int, default=300,
                        help='Check interval in seconds (default: 300)')
    parser.add_argument('-o', '--once', action='store_true',
                        help='Process once and exit (don\'t run continuously)')

    args = parser.parse_args()

    def process_arg(arg_value: str, env_var: str, arg_name: str) -> str:
        """Helper to process argument with environment variable fallback."""
        if arg_value:
            return arg_value
        env_value = os.getenv(env_var)
        if env_value:
            return env_value
        print(f"Error: {arg_name} must be provided via --{arg_name} "
              f"argument or {env_var} environment variable")
        sys.exit(1)

    # Get password from environment if not provided
    username = process_arg(args.username, 'IMAP_USERNAME', 'username')
    password = process_arg(args.password, 'IMAP_PASSWORD', 'password')
    domain = process_arg(args.domain, 'PRIMARY_DOMAIN', 'domain')
    server = process_arg(args.server, 'IMAP_SERVER', 'server')

    # Create processor
    processor = MTFSSProcessor(server, username, password, domain)
    # Connect to server
    if not processor.connect():
        sys.exit(1)

    try:

        if args.once:
            # Process once and exit
            processor.process_inbox()
        else:
            # Run continuously
            processor.run_continuous(args.interval)

    finally:
        if processor.connection and processor.connection.state == 'LOGOUT':
            processor.disconnect()


if __name__ == '__main__':
    main()
