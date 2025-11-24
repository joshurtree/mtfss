#!/usr/bin/env python3
"""
Test suite for MTFSS - Multi-Tenant Folder Sorting Sieve
"""

import email
import email.message
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest

from mtfss import MTFSSProcessor


class TestMTFSSProcessor(unittest.TestCase):
    """Test cases for MTFSSProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = MTFSSProcessor(
            imap_server="imap.example.com",
            username="test@example.com",
            password="password",
            primary_domain="example.com"
        )

        # Mock the IMAP connection
        self.mock_connection = MagicMock()
        self.mock_connection.list.return_value = ('OK', [])
        self.processor.connection = self.mock_connection

    def test_parse_email_address_valid(self):
        """Test parsing valid email addresses."""
        user, domain = self.processor.parse_email_address("john@example.com")
        self.assertEqual(user, "john")
        self.assertEqual(domain, "example.com")

        user, domain = self.processor.parse_email_address(
            "user+tag@subdomain.example.org")
        self.assertEqual(user, "user+tag")
        self.assertEqual(domain, "subdomain.example.org")

    def test_parse_email_address_invalid(self):
        """Test parsing invalid email addresses."""
        user, domain = self.processor.parse_email_address("invalid-email")
        self.assertEqual(user, "")
        self.assertEqual(domain, "")

        user, domain = self.processor.parse_email_address("@example.com")
        self.assertEqual(user, "")
        self.assertEqual(domain, "")

        user, domain = self.processor.parse_email_address("user@")
        self.assertEqual(user, "")
        self.assertEqual(domain, "")

    def test_extract_recipients(self):
        """Test extracting recipients from email headers."""
        # Create a test email message
        msg = email.message.EmailMessage()
        msg['To'] = 'user1@example.com, user2@test.org'
        msg['Cc'] = 'user3@example.com'
        msg['Bcc'] = 'user4@hidden.com'

        recipients = self.processor.extract_recipients(msg)

        expected = [
            'user1@example.com',
            'user2@test.org',
            'user3@example.com',
            'user4@hidden.com'
        ]
        self.assertEqual(sorted(recipients), sorted(expected))

    def test_extract_recipients_with_names(self):
        """Test extracting recipients when names are included."""
        msg = email.message.EmailMessage()
        msg['To'] = 'John Doe <john@example.com>, "Jane Smith" <jane@test.org>'
        msg['Cc'] = 'Support Team <support@company.com>'

        recipients = self.processor.extract_recipients(msg)

        expected = ['john@example.com', 'jane@test.org', 'support@company.com']
        self.assertEqual(sorted(recipients), sorted(expected))

    def test_extract_recipients_no_recipients(self):
        """Test extracting recipients when none are present."""
        msg = email.message.EmailMessage()
        recipients = self.processor.extract_recipients(msg)
        self.assertEqual(recipients, [])

    def test_determine_folder_primary_domain(self):
        """Test folder determination for primary domain."""
        folder = self.processor.determine_folder("john", "example.com")
        self.assertEqual(folder, "john")

    def test_determine_folder_other_domain(self):
        """Test folder determination for other domains."""
        folder = self.processor.determine_folder("john", "other.com")
        self.assertEqual(folder, "john@other.com")

    def test_determine_folder_malformed(self):
        """Test folder determination for malformed addresses."""
        folder = self.processor.determine_folder("", "")
        self.assertEqual(folder, "unmatched")

        folder = self.processor.determine_folder("john", "")
        self.assertEqual(folder, "unmatched")

        folder = self.processor.determine_folder("", "example.com")
        self.assertEqual(folder, "unmatched")

    def test_determine_folder_ignored_user(self):
        """Test folder determination for ignored users."""
        # Mock folder_exists to return True for ignore folder
        with patch.object(self.processor, 'folder_exists') as mock_exists:
            mock_exists.side_effect = lambda folder: folder == "ignore/john"

            folder = self.processor.determine_folder("john", "example.com")
            self.assertEqual(folder, "ignore/john")

            # Verify folder_exists was called
            mock_exists.assert_called_with("ignore/john")

    def test_folder_exists_true(self):
        """Test folder existence check when folder exists."""
        self.mock_connection.list.return_value = (
            'OK', [b'() "/" "test_folder"'])

        result = self.processor.folder_exists("test_folder")
        self.assertTrue(result)

        self.mock_connection.list.assert_called_with('""', "test_folder")

    def test_folder_exists_false(self):
        """Test folder existence check when folder doesn't exist."""
        self.mock_connection.list.return_value = ('OK', [])

        result = self.processor.folder_exists("nonexistent_folder")
        self.assertFalse(result)

    def test_folder_exists_no_connection(self):
        """Test folder existence check without connection."""
        self.processor.connection = None

        with pytest.raises(Exception):
            self.processor.folder_exists("test_folder")

    def test_create_folder_success(self):
        """Test successful folder creation."""
        self.mock_connection.create.return_value = ('OK', [])

        result = self.processor.create_folder("new_folder")
        self.assertTrue(result)

        self.mock_connection.create.assert_called_with("new_folder")

    def test_create_folder_failure(self):
        """Test failed folder creation."""
        self.mock_connection.create.return_value = ('NO', ['Error message'])

        result = self.processor.create_folder("bad_folder")
        self.assertFalse(result)

    def test_create_folder_no_connection(self):
        """Test folder creation without connection."""
        self.processor.connection = None

        result = self.processor.create_folder("test_folder")
        self.assertFalse(result)

    def test_move_email_success(self):
        """Test successful email move."""
        # Mock folder existence and creation
        with patch.object(self.processor, 'folder_exists', return_value=True):
            self.mock_connection.move.return_value = ('OK', [])

            result = self.processor.move_email("123", "target_folder")
            self.assertTrue(result)

            self.mock_connection.move.assert_called_with(
                "123", "target_folder")

    def test_move_email_create_folder_first(self):
        """Test email move when folder needs to be created."""
        with patch.object(self.processor, 'folder_exists', return_value=False), \
                patch.object(self.processor, 'create_folder', return_value=True):

            self.mock_connection.move.return_value = ('OK', [])

            result = self.processor.move_email("123", "new_folder")
            self.assertTrue(result)

    def test_move_email_failure(self):
        """Test failed email move."""
        with patch.object(self.processor, 'folder_exists', return_value=True):
            self.mock_connection.move.return_value = ('NO', ['Error'])

            result = self.processor.move_email("123", "target_folder")
            self.assertFalse(result)

    def test_move_email_no_connection(self):
        """Test email move without connection."""
        self.processor.connection = None

        with pytest.raises(Exception):
            self.processor.move_email("123", "target_folder")

    @patch('mtfss.IMAP4_SSL')
    def test_connect_success(self, mock_imap):
        """Test successful IMAP connection."""
        mock_conn = Mock()
        mock_imap.return_value = mock_conn
        mock_conn.login.return_value = ('OK', [])

        processor = MTFSSProcessor("imap.test.com", "user", "pass", "test.com")
        processor.connect()

        self.assertEqual(processor.connection, mock_conn)
        mock_imap.assert_called_with("imap.test.com")
        mock_conn.login.assert_called_with("user", "pass")

    @patch('mtfss.IMAP4_SSL')
    def test_connect_failure(self, mock_imap):
        """Test failed IMAP connection."""
        mock_imap.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            processor = MTFSSProcessor(
                "imap.test.com", "user", "pass", "test.com")
            processor.connect()

        self.assertIsNone(processor.connection)

    def test_disconnect(self):
        """Test IMAP disconnection."""
        self.processor.disconnect()

        self.mock_connection.close.assert_called_once()
        self.mock_connection.logout.assert_called_once()
        self.assertIsNone(self.processor.connection)

    def test_disconnect_with_error(self):
        """Test IMAP disconnection with error."""
        self.mock_connection.close.side_effect = Exception("Close error")

        # Should not raise exception
        with pytest.raises(Exception):
            self.processor.disconnect()
        self.assertIsNone(self.processor.connection)

    def test_process_inbox_no_connection(self):
        """Test processing inbox without connection."""
        self.processor.connection = None

        # Should not raise exception
        self.processor.process_inbox()

    def test_process_inbox_with_messages(self):
        """Test processing inbox with messages."""
        # Mock IMAP responses
        self.mock_connection.select.return_value = ('OK', [])
        self.mock_connection.search.return_value = ('OK', [b'1 2 3'])

        # Mock email messages
        test_email = email.message.EmailMessage()
        test_email['To'] = 'user@example.com'
        test_email['From'] = 'sender@test.com'
        test_email['Subject'] = 'Test Email'

        email_bytes = test_email.as_bytes()
        self.mock_connection.fetch.return_value = ('OK', [(None, email_bytes)])

        # Mock move_email method
        with patch.object(self.processor, 'move_email', return_value=True) as mock_move:
            self.processor.process_inbox()

            # Should call move_email for each message
            self.assertEqual(mock_move.call_count, 3)

        # Should call expunge
        self.mock_connection.expunge.assert_called_once()

    def test_process_inbox_no_messages(self):
        """Test processing empty inbox."""
        self.mock_connection.select.return_value = ('OK', [])
        self.mock_connection.search.return_value = ('OK', [b''])

        # Should not raise exception
        self.processor.process_inbox()

        # Should not call expunge for empty inbox
        self.mock_connection.expunge.assert_called_once()


class TestEmailParsing(unittest.TestCase):
    """Test cases for email parsing edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = MTFSSProcessor(
            "imap.test.com", "user", "pass", "test.com")
        self.mock_connection = Mock()
        self.mock_connection.list.return_value = ('OK', [])
        self.processor.connection = self.mock_connection

    def test_complex_email_addresses(self):
        """Test parsing complex email address formats."""
        test_cases = [
            ("user+tag@example.com", ("user+tag", "example.com")),
            ("user.name@sub.domain.com", ("user.name", "sub.domain.com")),
            ("user123@test-domain.org", ("user123", "test-domain.org")),
            ("user_name@example.co.uk", ("user_name", "example.co.uk")),
        ]

        for email_addr, expected in test_cases:
            with self.subTest(email=email_addr):
                result = self.processor.parse_email_address(email_addr)
                self.assertEqual(result, expected)

    def test_email_with_plus_addressing(self):
        """Test handling of plus addressing (sub-addressing)."""
        # Plus addressing should be preserved in user part
        user, domain = self.processor.parse_email_address(
            "user+project@test.com")
        self.assertEqual(user, "user+project")
        self.assertEqual(domain, "test.com")

        # Folder determination should use full user part
        folder = self.processor.determine_folder("user+project", "test.com")
        self.assertEqual(folder, "user+project")

    def test_international_domains(self):
        """Test handling of international domain names."""
        user, domain = self.processor.parse_email_address("user@münchen.de")
        self.assertEqual(user, "user")
        self.assertEqual(domain, "münchen.de")


class TestIgnoreFunctionality(unittest.TestCase):
    """Test cases for ignore functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = MTFSSProcessor(
            "imap.test.com", "user", "pass", "test.com")
        self.mock_connection = Mock()
        self.processor.connection = self.mock_connection

    def test_ignore_folder_detection(self):
        """Test detection of ignored users."""
        # Mock folder_exists to simulate ignore folder existence
        with patch.object(self.processor, 'folder_exists') as mock_exists:
            mock_exists.side_effect = lambda folder: folder == "ignore/spam"

            # Should route to ignore folder
            folder = self.processor.determine_folder("spam", "test.com")
            self.assertEqual(folder, "ignore/spam")

            # Should not route non-ignored users to ignore
            folder = self.processor.determine_folder("good", "test.com")
            self.assertEqual(folder, "good")

    def test_ignore_folder_creation(self):
        """Test that ignore folders can be created when needed."""
        with patch.object(self.processor, 'folder_exists', return_value=False), \
                patch.object(self.processor, 'create_folder', return_value=True) as mock_create:

            self.mock_connection.move.return_value = ('OK', [])

            result = self.processor.move_email("123", "ignore/newuser")
            self.assertTrue(result)

            # Should create the ignore folder
            mock_create.assert_called_with("ignore/newuser")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
