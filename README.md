# MTFSS - Multi-Tenant Folder Sorting Sieve

A Python script that automatically organizes emails into folders based on recipient addresses using IMAP.

## Features

- **Automatic Email Sorting**: Routes emails to folders based on recipient addresses
- **Primary Domain Support**: Configurable primary domain for user-specific folders
- **Ignore Functionality**: Automatically filters emails to ignored users
- **Continuous Monitoring**: Runs continuously to process new emails as they arrive
- **Comprehensive Testing**: Full test suite with edge case coverage
- **Container Support**: Docker/Podman container for easy deployment

## Email Routing Logic

- **Primary domain emails** (`user@yourdomain.com`): → `user` folder
- **Other domain emails** (`user@otherdomain.com`): → `user@otherdomain.com` folder  
- **Ignored users**: → `ignore/user` folder
- **Malformed addresses**: → `unmatched` folder

## Quick Start

### Local Installation

```bash
# Clone the repository
git clone <repository-url>
cd mtfss

# Run tests
python -m unittest test_mtfss -v

# Run the processor (example)
python mtfss.py \
    --server imap.gmail.com \
    --username your-email@gmail.com \
    --domain gmail.com \
    --interval 30
```

### Using Container

```bash
# Build container
podman build -t mtfss .

# Run with environment variables
podman run -e IMAP_SERVER=imap.gmail.com \
           -e IMAP_USERNAME=your-email@gmail.com \
           -e IMAP_PASSWORD=your-password \
           -e PRIMARY_DOMAIN=gmail.com \
           mtfss

# Run once and exit (for testing)
podman run -it mtfss python mtfss.py \
    --server imap.gmail.com \
    --username your-email@gmail.com \
    --domain gmail.com \
    --once
```

### Development Container

Open this project in VS Code and use the "Reopen in Container" command to automatically set up a development environment with all necessary tools and extensions.

## Configuration

### Command Line Arguments

- `--server`: IMAP server hostname (required)
- `--username`: IMAP username (required)  
- `--password`: IMAP password (optional, can use `IMAP_PASSWORD` env var)
- `--domain`: Primary domain for user folder routing (required)
- `--interval`: Check interval in seconds (default: 30)
- `--once`: Process once and exit instead of running continuously

### Environment Variables

- `IMAP_PASSWORD`: IMAP password (alternative to --password)
- `IMAP_SERVER`: IMAP server hostname
- `IMAP_USERNAME`: IMAP username
- `PRIMARY_DOMAIN`: Primary domain
- `CHECK_INTERVAL`: Check interval in seconds

## Testing

```bash
# Run all tests
python -m unittest test_mtfss -v

# Run specific test class
python -m unittest test_mtfss.TestMTFSSProcessor -v

# Run with pytest (if installed)
pytest test_mtfss.py -v
```

## Ignore Functionality

To ignore emails for a specific user:

1. Create an `ignore/username` folder on your IMAP server
2. Move unwanted emails to this folder
3. MTFSS will automatically route future emails to this folder

## Architecture

The main components:

- **MTFSSProcessor**: Core class handling IMAP operations and email routing
- **Email parsing**: Regex-based extraction of user/domain from recipient addresses  
- **Folder management**: Dynamic folder creation and existence checking
- **Continuous monitoring**: Loop with configurable check intervals

## Contributing

1. Use the development container for consistent environment
2. Run tests before submitting changes: `python -m unittest test_mtfss -v`
3. Follow Python code style guidelines (Black, isort, flake8)
4. Add tests for new functionality