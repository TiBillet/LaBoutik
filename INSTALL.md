# TiBillet/LaBoutik Installation Guide

This guide explains how to install TiBillet/LaBoutik using the automated scripts provided in this repository.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ with Poetry installed
- Access to a Fedow instance
- Access to a LesPass instance

## Installation Steps

### 1. Generate the .env file

The first step is to generate a `.env` file with the necessary configuration. You can use the `env_generator.py` script for this:

```bash
# Interactive mode (recommended for first-time users)
python env_generator.py

# Non-interactive mode with default values
python env_generator.py --non-interactive

# Test mode with predefined values
python env_generator.py --test
```

The script will prompt you for the necessary values and generate a `.env` file in the project root.

### 2. Install TiBillet/LaBoutik

Once you have generated the `.env` file, you can install TiBillet/LaBoutik using one of the following methods:

#### 2.1 Using Docker Compose (Recommended for Production)

```bash
# Start the Docker containers
docker-compose up -d

# Enter the Django container
docker exec -it laboutik_django bash

# Run the installation script
python manage.py install_with_fixture
```

#### 2.2 Using the flush_with_fixture.sh script (Recommended for Development)

```bash
# For test/development mode
export TEST=1
./flush_with_fixture.sh

# For production mode
./flush_with_fixture.sh
```

The script will:
1. Flush the database
2. Run migrations
3. Load the appropriate fixture (test or production)
4. Update the configuration with values from the .env file
5. Perform handshakes with Fedow and LesPass
6. Create an admin user
7. Collect static files
8. Start the development server (in test mode)

### 3. Verify the Installation

After the installation is complete, you can verify that everything is working correctly by:

1. Accessing the admin interface at `https://your-domain/admin/`
2. Logging in with the admin email and password (you should have received an activation email)
3. Checking that the configuration, payment methods, and other objects have been created correctly

## Fixture-Based Installation vs. Traditional Installation

This repository provides two methods for installing TiBillet/LaBoutik:

1. **Traditional Installation** (`install.py` and `flush.sh`): Creates all objects directly in the database.
2. **Fixture-Based Installation** (`install_with_fixture.py` and `flush_with_fixture.sh`): Loads objects from fixture files and then updates them with values from the .env file.

The fixture-based installation is recommended because:
- It's faster, as it loads pre-defined objects instead of creating them one by one
- It's more reliable, as it ensures that all required objects are created
- It includes tests to verify that the installation was successful

## Troubleshooting

If you encounter any issues during installation, check the following:

1. Make sure your `.env` file contains all the required values
2. Make sure the Fedow and LesPass instances are accessible
3. Check the logs for any error messages
4. Try running the installation with the `--skip-handshake` flag to skip the Fedow and LesPass handshakes:

```bash
python manage.py install_with_fixture --skip-handshake
```

If you continue to experience issues, please open an issue on the GitHub repository.