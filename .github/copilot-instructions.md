# Copilot Instructions for MTFSS

This repository contains **MTFSS** (Multi-Tenant Folder Sorting Sieve) - python script that automatically organizes emails into folders based on recipient addresses.

## Project Architecture

**Core file**: `mtfss.py` - The main Sieve script that implements email filtering logic
- Establishes connection to an IMAP server
- Once connected, it processes any new emails in the inbox, then sorts them into appropriate folders based on the recipient addresses.
- It stays connected to the IMAP server to continuously monitor for new emails.
- Uses a the primary domain set as an environment variable or passed as a command-line argument (currently hardcoded)
- Extracts user and domain parts from recipient addresses using regex
- Routes emails to user-specific folders or domain-based folders
- Implements ignore functionality for unwanted users

## Key Implementation Details

** Required libraries **:
- imaplib
- email
- re

**Email routing logic**:
- For primary domain `user`@`domain`: creates folder named `user` 
- For other domains: creates folder named `user`@`domain`
- Emails are moved into the appropriate folder
- Malformed addresses go to `unmatched` folder
- Ignored users go to ignore/`user` folder
- For all logic, the regex is performed on the envelope "to" address first, if that fails, then test on the "CC" and "BCC" headers. 

**Ignore functionality**:
- If a message is sent to an ignored user, it is automatically moved to the ignore/`user` folder.
- An ignored user is determined by checking if the ignore/`user` folder exists.
- The `user` folder is deleted to stop future emails from being delivered to that user.

## Development Guidelines

**When modifying the script**:
1. Test regex patterns carefully - envelope parsing is critical
2. Add comments for complex logic, especially regex patterns
3. Handle edge cases like missing envelope data

**Testing approach**:
- Test with various email formats: `user@domain.com`, `user+tag@domain.com`
- Test ignore functionality by creating ignore folders
- Verify folder creation works for both user folders and domain folders
- Test malformed address handling

## Primary Files

- Main script: `mtfss.py`
- Test script: `test_mtfss.py`
- Containerization: `Containerfile`

## Integration Notes

- Create a dev container for development and testing purposes
- This script should be used within a container with access to an IMAP server 