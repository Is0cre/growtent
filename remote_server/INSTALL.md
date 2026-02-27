# Grow Tent Monitor - Installation Guide

Detailed instructions for setting up the remote LAMP server.

## Prerequisites

- Ubuntu 20.04/22.04 LTS server (or similar Linux distribution)
- Root or sudo access
- Network connectivity to the Raspberry Pi

## Step 1: Install LAMP Stack

### Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### Install Apache
```bash
sudo apt install apache2 -y
sudo a2enmod rewrite headers deflate expires
sudo systemctl enable apache2
```

### Install MySQL
```bash
sudo apt install mysql-server -y
sudo mysql_secure_installation
```

### Install PHP
```bash
sudo apt install php php-mysql php-sqlite3 php-json php-mbstring php-curl -y
```

### Verify Installation
```bash
php -v
mysql --version
apache2 -v
```

## Step 2: Set Up the Application

### Create Web Directory
```bash
sudo mkdir -p /var/www/grow-tent
sudo chown -R $USER:www-data /var/www/grow-tent
```

### Copy Application Files
```bash
# From this repository
cp -r remote_server/* /var/www/grow-tent/

# Set permissions
sudo chown -R www-data:www-data /var/www/grow-tent
sudo chmod -R 755 /var/www/grow-tent
sudo chmod -R 775 /var/www/grow-tent/public/data
```

### Create Data Directories
```bash
sudo mkdir -p /var/www/grow-tent/public/data/{photos,timelapse,diary}
sudo chown -R www-data:www-data /var/www/grow-tent/public/data
```

## Step 3: Configure MySQL

### Create Database and User
```bash
sudo mysql -u root -p
```

```sql
-- Create database
CREATE DATABASE grow_tent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'grow_tent_user'@'localhost' IDENTIFIED BY 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON grow_tent.* TO 'grow_tent_user'@'localhost';
FLUSH PRIVILEGES;

-- Import schema
USE grow_tent;
SOURCE /var/www/grow-tent/sql/schema.sql;

EXIT;
```

### Configure Application Database
```bash
cd /var/www/grow-tent/config
cp database.php database.local.php
nano database.local.php
```

Update the credentials:
```php
<?php
return [
    'host' => 'localhost',
    'port' => 3306,
    'database' => 'grow_tent',
    'username' => 'grow_tent_user',
    'password' => 'your_secure_password',
    'charset' => 'utf8mb4',
    'collation' => 'utf8mb4_unicode_ci',
    'options' => [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ],
    'sqlite_source' => '/tmp/grow_tent.db'
];
```

## Step 4: Configure Apache

### Create Virtual Host
```bash
sudo nano /etc/apache2/sites-available/grow-tent.conf
```

Add the following:
```apache
<VirtualHost *:80>
    ServerName grow-tent.example.com
    ServerAlias grow-tent.local
    DocumentRoot /var/www/grow-tent/public
    
    <Directory /var/www/grow-tent/public>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    
    # Logging
    ErrorLog ${APACHE_LOG_DIR}/grow-tent-error.log
    CustomLog ${APACHE_LOG_DIR}/grow-tent-access.log combined
    
    # PHP settings
    <FilesMatch \.php$>
        SetHandler application/x-httpd-php
    </FilesMatch>
</VirtualHost>
```

### Enable Site
```bash
sudo a2ensite grow-tent.conf
sudo a2dissite 000-default.conf  # Optional: disable default site
sudo systemctl reload apache2
```

### Test Apache Configuration
```bash
sudo apache2ctl configtest
```

## Step 5: Set Up SSH Keys for Rsync

### Generate SSH Key (on LAMP server)
```bash
sudo -u www-data ssh-keygen -t ed25519 -C "grow-tent-sync" -f /var/www/.ssh/id_ed25519 -N ""
```

### Copy Key to Raspberry Pi
```bash
# Display public key
sudo cat /var/www/.ssh/id_ed25519.pub

# SSH to Pi and add to authorized_keys
ssh matthias@grow-tent
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
# Paste the public key
chmod 600 ~/.ssh/authorized_keys
exit
```

### Test SSH Connection
```bash
sudo -u www-data ssh -i /var/www/.ssh/id_ed25519 matthias@grow-tent "echo 'Connection successful'"
```

## Step 6: Configure Rsync Script

### Update Script Configuration
```bash
sudo nano /var/www/grow-tent/scripts/sync_from_pi.sh
```

Update these variables:
```bash
PI_USER="matthias"
PI_HOST="grow-tent"  # Or IP address like 192.168.1.50
PI_DATA_PATH="/home/matthias/grow_tent_automation/data"
LOCAL_DATA_PATH="/var/www/grow-tent/public/data"
SCRIPTS_PATH="/var/www/grow-tent/scripts"
```

### Make Script Executable
```bash
sudo chmod +x /var/www/grow-tent/scripts/sync_from_pi.sh
```

### Create Log File
```bash
sudo touch /var/log/grow-tent-sync.log
sudo chown www-data:www-data /var/log/grow-tent-sync.log
```

### Test Sync Script
```bash
sudo -u www-data /var/www/grow-tent/scripts/sync_from_pi.sh -v
```

## Step 7: Set Up Cron Job

### Edit www-data Crontab
```bash
sudo crontab -u www-data -e
```

Add the following:
```cron
# Sync from Raspberry Pi every 5 minutes
*/5 * * * * /var/www/grow-tent/scripts/sync_from_pi.sh >> /var/log/grow-tent-sync.log 2>&1

# Clean up old log entries weekly
0 0 * * 0 find /var/log/grow-tent-sync.log -size +10M -exec truncate -s 0 {} \;
```

## Step 8: Optional - Enable HTTPS

### Install Certbot
```bash
sudo apt install certbot python3-certbot-apache -y
```

### Obtain Certificate
```bash
sudo certbot --apache -d grow-tent.example.com
```

### Auto-Renewal (already set up by certbot)
```bash
sudo certbot renew --dry-run
```

## Step 9: Optional - Enable Authentication

### Create htpasswd File
```bash
sudo htpasswd -c /var/www/grow-tent/.htpasswd admin
```

### Enable Authentication
Edit `config/config.php`:
```php
define('REQUIRE_AUTH', true);
```

## Step 10: Verify Installation

### Check List

- [ ] Apache is running: `sudo systemctl status apache2`
- [ ] MySQL is running: `sudo systemctl status mysql`
- [ ] Web page loads: Open `http://your-server/` in browser
- [ ] API responds: `curl http://your-server/api/current_data.php`
- [ ] Sync works: Check `/var/log/grow-tent-sync.log`
- [ ] Data directory has files: `ls -la /var/www/grow-tent/public/data/`

### Test API Endpoints
```bash
# Current data
curl -s http://localhost/api/current_data.php | jq .

# Sensor history
curl -s "http://localhost/api/sensor_history.php?hours=24" | jq .

# Projects
curl -s http://localhost/api/projects.php | jq .
```

## Troubleshooting

### Common Issues

#### "500 Internal Server Error"
```bash
# Check Apache error log
sudo tail -f /var/log/apache2/grow-tent-error.log

# Check PHP errors
sudo tail -f /var/log/php*.log
```

#### Database Connection Failed
```bash
# Test MySQL connection
mysql -u grow_tent_user -p grow_tent -e "SELECT 1;"

# Check PHP MySQL extension
php -m | grep mysql
```

#### Rsync Permission Denied
```bash
# Check SSH key permissions
sudo ls -la /var/www/.ssh/

# Test SSH connection manually
sudo -u www-data ssh -vvv matthias@grow-tent
```

#### No Data After Sync
```bash
# Check if SQLite file exists
ls -la /tmp/grow_tent.db

# Run import manually
sudo -u www-data php /var/www/grow-tent/scripts/import_data.php
```

### Useful Commands

```bash
# View sync log
tail -f /var/log/grow-tent-sync.log

# Check cron jobs
sudo crontab -u www-data -l

# Restart Apache
sudo systemctl restart apache2

# Check disk space
df -h

# Check data directory size
du -sh /var/www/grow-tent/public/data/*
```

## Maintenance

### Backup Database
```bash
mysqldump -u grow_tent_user -p grow_tent > backup_$(date +%Y%m%d).sql
```

### Clean Old Data
```bash
# Delete sensor logs older than 1 year
mysql -u grow_tent_user -p grow_tent -e "DELETE FROM sensor_logs WHERE timestamp < DATE_SUB(NOW(), INTERVAL 1 YEAR);"
```

### Update Application
```bash
# Pull latest changes
cd /var/www/grow-tent
git pull origin main

# Reset permissions
sudo chown -R www-data:www-data /var/www/grow-tent
```

## Support

If you encounter issues:

1. Check the logs (`/var/log/apache2/`, `/var/log/grow-tent-sync.log`)
2. Verify all configuration files have correct values
3. Ensure network connectivity between server and Pi
4. Check file permissions on all directories
