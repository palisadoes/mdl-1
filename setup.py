#!/usr/bin/env python3
"""mdl ORM classes.

Manages connection pooling among other things.

"""

# Main python libraries
import sys
import os
import getpass
from pwd import getpwnam
import grp
import copy
import re

# PIP3 imports
import yaml
from sqlalchemy import create_engine

# mdl libraries
try:
    from mdl.utils import log
except:
    print(
        'You need to set your PYTHONPATH to include the '
        'mdl root directory')
    sys.exit(2)
from mdl.utils import configuration
from mdl.utils import general
from mdl.db.db_orm import BASE, DeviceMakes, DeviceModels, Routes, Riders
from mdl.db.db_orm import DriverCompanies, RiderDevices, DriverDevices, Drivers
from mdl.db import URL, db
from mdl.db import db_devicemake
from mdl.db import db_devicemodel
from mdl.db import db_route
from mdl.db import db_rider
from mdl.db import db_driver
from mdl.db import db_drivercompany
from mdl.db import db_riderdevice
from mdl.db import db_driverdevice


class _Database(object):
    """Class to setup database."""

    def __init__(self):
        """Function for intializing the class.

        Args:
            None

        Returns:
            None

        """
        # Initialize key variables
        self.reserved = '_SYSTEM_RESERVED_'
        self.config = configuration.Config()

    def setup(self):
        """Setup database.

        Args:
            None

        Returns:
            None

        """
        # Initialize key variables
        use_mysql = True
        pool_size = 25
        max_overflow = 25
        config = self.config

        # Create DB connection pool
        if use_mysql is True:
            # Add MySQL to the pool
            engine = create_engine(
                URL, echo=True,
                encoding='utf8',
                max_overflow=max_overflow,
                pool_size=pool_size, pool_recycle=3600)

            # Try to create the database
            print('Attempting to create database tables')
            try:
                sql_string = (
                    'ALTER DATABASE %s CHARACTER SET utf8mb4 '
                    'COLLATE utf8mb4_general_ci') % (config.db_name())
                engine.execute(sql_string)
            except:
                log_message = (
                    'Cannot connect to database %s. '
                    'Verify database server is started. '
                    'Verify database is created. '
                    'Verify that the configured database authentication '
                    'is correct.') % (config.db_name())
                log.log2die(1036, log_message)

            # Apply schemas
            print('Applying Schemas')
            BASE.metadata.create_all(engine)

        # Add starter rows to tables
        self._add_records()

    def _add_records(self):
        """Add initial records to database tables.

        Args:
            None

        Returns:
            None

        """
        # Insert DeviceMake
        if db_devicemake.idx_devicemake_exists(1) is False:
            record = DeviceMakes(
                make_name=general.encode(self.reserved),
                enabled=0
            )
            database = db.Database()
            database.add(record, 1000)

        # Insert DeviceModel
        if db_devicemodel.idx_devicemodel_exists(1) is False:
            record = DeviceModels(
                model_name=general.encode(self.reserved),
                enabled=0
            )
            database = db.Database()
            database.add(record, 1001)

        # Insert Route
        if db_route.idx_route_exists(1) is False:
            record = Routes(
                route_name=general.encode(self.reserved),
                enabled=0
            )
            database = db.Database()
            database.add(record, 1002)

        # Insert Rider
        if db_rider.idx_rider_exists(1) is False:
            record = Riders(
                first_name=general.encode(self.reserved),
                last_name=general.encode(self.reserved),
                password=general.encode(self.reserved),
                enabled=0
            )
            database = db.Database()
            database.add(record, 1003)

        # Insert DriverCompany
        if db_drivercompany.idx_drivercompany_exists(1) is False:
            record = DriverCompanies(
                drivercompany_name=general.encode(self.reserved),
                enabled=0
            )
            database = db.Database()
            database.add(record, 1004)

        # Insert Driver
        if db_driver.idx_driver_exists(1) is False:
            record = Drivers(
                first_name=general.encode(self.reserved),
                last_name=general.encode(self.reserved),
                password=general.encode(self.reserved),
                enabled=0
            )
            database = db.Database()
            database.add(record, 1005)

        # Insert RiderDevice
        if db_riderdevice.idx_riderdevice_exists(1) is False:
            record = RiderDevices(
                id_riderdevice=general.encode(self.reserved),
                serial_riderdevice=general.encode(self.reserved),
                enabled=0
            )
            database = db.Database()
            database.add(record, 1006)

        # Insert DriverDevice
        if db_driverdevice.idx_driverdevice_exists(1) is False:
            record = DriverDevices(
                id_driverdevice=general.encode(self.reserved),
                serial_driverdevice=general.encode(self.reserved),
                enabled=0
            )
            database = db.Database()
            database.add(record, 1007)


class _Configuration(object):
    """Class to setup configuration.

    NOTE! We cannot use the configuration.Config class here. The aim
    of this class is to read in the configuration found in etc/ or
    $MDL_CONFIGDIR and set any missing values to values that are
    known to work in most cases.

    """

    def __init__(self):
        """Function for intializing the class.

        Args:
            None

        Returns:
            None

        """
        # Read configuration into dictionary
        self.directories = general.config_directories()
        self.config = general.read_yaml_files(self.directories)

    def setup(self):
        """Update the configuration with good defaults.

        Args:
            None

        Returns:
            None

        """
        # Initialize key variables
        valid = True
        updated_list = []
        config = copy.deepcopy(self.config)
        directory = self.directories[0]

        # Update log_directory and ingest_cache_directory
        if isinstance(config, dict) is True:
            if 'main' in config:
                # Setup the log_directory to a known good default
                (updated, config) = self._create_directory_entries(
                    'log_directory', config)
                updated_list.append(updated)

            else:
                valid = False
        else:
            valid = False

        # Gracefully exit if things are not OK
        if valid is False:
            log_message = (
                'Configuration files found in {} is invalid'
                ''.format(self.directories))
            log.log2die_safe(1015, log_message)

        # Update configuration file if required
        if len(updated_list) == updated_list.count(True):
            for next_directory in self.directories:
                # Delete all YAML files in the directory
                general.delete_yaml_files(next_directory)

            # Write config back to directory
            filepath = ('%s/config.yaml') % (directory)
            with open(filepath, 'w') as outfile:
                yaml.dump(config, outfile, default_flow_style=False)

    def _create_directory_entries(self, key, config):
        """Update the configuration with good defaults for directories.

        Args:
            key: Configuration key related to a directory.
            config: Configuration dictionary

        Returns:
            updated: True if we have to update a value

        """
        # Initialize key variables
        updated = False
        dir_dict = {
            'log_directory': 'log',
            'ingest_cache_directory': 'cache',
        }
        directory = general.root_directory()

        # Setup the key value to a known good default
        if key in config['main']:
            # Verify whether key value is empty
            if config['main'][key] is not None:
                # Create
                if os.path.isdir(config['main'][key]) is False:
                    config['main'][key] = ('%s/%s') % (
                        directory, dir_dict[key])
                    updated = True
            else:
                config['main'][key] = ('%s/%s') % (directory, dir_dict[key])
                updated = True
        else:
            config['main'][key] = ('%s/%s') % (directory, dir_dict[key])
            updated = True

        # Return
        return (updated, config)


class _Python(object):
    """Class to setup Python."""

    def __init__(self):
        """Function for intializing the class.

        Args:
            None

        Returns:
            None

        """
        # Initialize key variables
        self.username = getpass.getuser()
        valid = True
        major = 3
        minor = 5
        major_installed = sys.version_info[0]
        minor_installed = sys.version_info[1]

        # Exit if python version is too low
        if major_installed < major:
            valid = False
        elif major_installed == major and minor_installed < minor:
            valid = False
        if valid is False:
            log_message = (
                'Required python version must be >= {}.{}. '
                'Python version {}.{} installed'
                ''.format(major, minor, major_installed, minor_installed))
            log.log2die_safe(1018, log_message)

    def setup(self):
        """Setup Python.

        Args:
            None

        Returns:
            None

        """
        # Run
        self._install_pip3_packages()

    def _install_pip3_packages(self):
        """Install PIP3 packages.

        Args:
            None

        Returns:
            None

        """
        # Initialize key variables
        username = self.username

        # Don't attempt to install packages if running in the Travis CI
        # environment
        if 'TRAVIS' in os.environ and 'CI' in os.environ:
            return

        # Determine whether PIP3 exists
        print('Installing required pip3 packages')
        pip3 = general.search_file('pip3')
        if pip3 is None:
            log_message = ('Cannot find python "pip3". Please install.')
            log.log2die_safe(1052, log_message)

        # Install required PIP packages
        requirements_file = (
            '%s/requirements.txt') % (general.root_directory())

        if username == 'root':
            script_name = (
                'pip3 install --upgrade --requirement %s'
                '') % (requirements_file)
        else:
            script_name = (
                'pip3 install --user --upgrade --requirement %s'
                '') % (requirements_file)
        general.run_script(script_name)


class _Daemon(object):
    """Class to setup mdl daemon."""

    def __init__(self):
        """Function for intializing the class.

        Args:
            None

        Returns:
            None

        """
        # Initialize key variables
        username = getpass.getuser()
        self.root_directory = general.root_directory()
        self.mdl_user_exists = True
        self.mdl_user = None
        self.running_as_root = False

        # If running as the root user, then the mdl user needs to exist
        if username == 'root':
            self.running_as_root = True
            try:
                self.mdl_user = input(
                    'Please enter the username under which '
                    'mdl will run: ')

                # Get GID and UID for user
                self.gid = getpwnam(self.mdl_user).pw_gid
                self.uid = getpwnam(self.mdl_user).pw_uid
            except KeyError:
                self.mdl_user_exists = False
            return

        # Die if user doesn't exist
        if self.mdl_user_exists is False:
            log_message = (
                'User {} not found. Please try again.'
                ''.format(self.mdl_user))
            log.log2die_safe(1049, log_message)

    def setup(self):
        """Setup daemon scripts and file permissions.

        Args:
            None

        Returns:
            None

        """
        # Set bashrc file
        self._bashrc()

        # Return if not running script as root user
        if self.running_as_root is False:
            return

        # Return if user prompted doesn't exist
        if self.mdl_user_exists is False:
            return

        # Set file permissions
        self._file_permissions()

        # Setup systemd
        self._systemd()

    def _bashrc(self):
        """Set bashrc file environment variables.

        Args:
            None

        Returns:
            None

        """
        # Initialize key variables
        root_directory = self.root_directory

        # Determine username to use
        if self.running_as_root is True:
            # Edit local user's bashrc file
            username = self.mdl_user
        else:
            # Edit selected user's bashrc file
            username = getpass.getuser()

        # Read bashrc file
        home_directory = os.path.expanduser('~{}'.format(username))
        filepath = '{}/.bashrc'.format(home_directory)

        # Do nothing if .bashrc file doesn't exist
        if (os.path.isfile(filepath) is False) or (
                os.path.exists(filepath) is False):
            return

        # Read contents of file
        with open(filepath, 'r') as f_handle:
            contents = f_handle.read()

        # Create string to append to the end of the file
        if 'PYTHONPATH' in contents:
            export_string = """\

# Automatically inserted by the mdl installation script
# It appended the requied PYTHONPATH to your your existing PYTHONPATH
PYTHONPATH=$PYTHONPATH:{}
export PYTHONPATH
""".format(root_directory)
        else:
            export_string = """\

# Automatically inserted by the mdl installation script
# It appended the requied PYTHONPATH to your your existing PYTHONPATH
PYTHONPATH={}
export PYTHONPATH
""".format(root_directory)

        # Append the PYTHONPATH to the end of the
        contents = '{}{}'.format(contents, export_string)
        with open(filepath, 'w') as f_handle:
            f_handle.write(contents)

    def _file_permissions(self):
        """Set file permissions.

        Args:
            None

        Returns:
            None

        """
        # Initialize key variables
        mdl_user = self.mdl_user
        root_directory = self.root_directory

        # Prompt to change ownership of root_directory
        groupname = grp.getgrgid(self.gid).gr_name
        response = input(
            'Change ownership of {} directory to user:{} group:{} (y,N) ?: '
            ''.format(root_directory, mdl_user, groupname))

        # Abort if necessary
        if response.lower() != 'y':
            log_message = ('Aborting as per user request.')
            log.log2die_safe(1050, log_message)

        # Change ownership of files under root_directory
        for parent_directory, directories, files in os.walk(root_directory):
            for directory in directories:
                os.chown(os.path.join(
                    parent_directory, directory), self.uid, self.gid)
            for next_file in files:
                os.chown(os.path.join(
                    parent_directory, next_file), self.uid, self.gid)

        # Change ownership of root_directory
        os.chown(root_directory, self.uid, self.gid)

    def _systemd(self):
        """Setup systemd configuration.

        Args:
            None

        Returns:
            None

        """
        # Initialize key variables
        username = self.mdl_user
        groupname = grp.getgrgid(self.gid).gr_name
        system_directory = '/etc/systemd/system'
        system_command = '/bin/systemctl daemon-reload'

        # Copy system files to systemd directory and activate
        service_api = (
            '{}/examples/linux/systemd/mdl-api.service'
            ''.format(self.root_directory))

        # Read in file
        # 1) Convert home directory to that of user
        # 2) Convert username in file
        # 3) Convert group in file
        filenames = [service_api]
        for filename in filenames:
            # Read next file
            with open(filename, 'r') as f_handle:
                contents = f_handle.read()

            # Substitute home directory
            contents = re.sub(
                r'/home/mdl',
                self.root_directory,
                contents)

            # Substitute username
            contents = re.sub(
                'User=mdl',
                'User={}'.format(username),
                contents)

            # Substitute group
            contents = re.sub(
                'Group=mdl',
                'Group={}'.format(groupname),
                contents)

            # Write contents
            filepath = (
                '{}/{}'.format(system_directory, os.path.basename(filename)))
            if os.path.isdir(system_directory):
                with open(filepath, 'w') as f_handle:
                    f_handle.write(contents)

        # Make systemd recognize new files
        if os.path.isdir(system_directory):
            general.run_script(system_command)


def main():
    """Process agent data.

    Args:
        None

    Returns:
        None

    """
    # Initialize key variables
    username = getpass.getuser()

    # Determine whether version of python is valid
    _Python().setup()

    # Do specific setups for root user
    _Daemon().setup()

    # Update configuration if required
    _Configuration().setup()

    # Run server setup
    _Database().setup()

    # Give suggestions as to what to do
    if username == 'root':
        suggestions = """\

You can start mdl daemons with these commands:

    # systemctl start mdl-api.service

You can enable mdl daemons to start on system boot with these commands:

    # systemctl enable mdl-api.service

"""
        print(suggestions)

    # Outline the versions of MySQL and MariaDB that are required
    suggestions = """\

mdl requires:

    MySQL >= 5.5
    MariaDB >= 10

Please verify.

"""
    print(suggestions)

    # All done
    print('\nOK\n')


if __name__ == '__main__':
    # Prevent running as sudo user
    if 'SUDO_UID' in os.environ:
        MESSAGE = (
            'Cannot run setup using "sudo". Run as a regular user to '
            'install in this directory or as user "root".')
        log.log2die_safe(1078, MESSAGE)

    # Run main
    main()
