# Grow Tent Monitor - Remote Server

A LAMP-based web application for displaying grow tent data synced from a Raspberry Pi.

## 🌱 Features

- **Real-time Dashboard**: View current sensor readings with animated gauges
- **Historical Data**: Interactive charts with date range selection
- **AI Analysis**: Browse health scores and plant analysis reports
- **Grow Diary**: Timeline view of diary entries with photos
- **Time-lapse Gallery**: Watch time-lapse videos and browse images
- **Project Management**: Track multiple grow projects

## 📋 Requirements

- **Server**: Linux server (Ubuntu 20.04+ recommended)
- **Web Server**: Apache 2.4+ with mod_rewrite
- **PHP**: 8.0+ with PDO, SQLite3, and MySQL extensions
- **Database**: MySQL 5.7+ or MariaDB 10.3+
- **Raspberry Pi**: Running the Grow Tent Automation system

## 🚀 Quick Start

1. **Clone to your web server:**
   ```bash
   sudo mkdir -p /var/www/grow-tent
   sudo cp -r . /var/www/grow-tent/
   sudo chown -R www-data:www-data /var/www/grow-tent
   ```

2. **Create MySQL database:**
   ```bash
   mysql -u root -p < sql/schema.sql
   ```

3. **Configure the application:**
   ```bash
   cp config/database.php config/database.local.php
   nano config/database.local.php  # Update credentials
   ```

4. **Set up Apache virtual host:**
   ```apache
   <VirtualHost *:80>
       ServerName grow-tent.local
       DocumentRoot /var/www/grow-tent/public
       
       <Directory /var/www/grow-tent/public>
           AllowOverride All
           Require all granted
       </Directory>
   </VirtualHost>
   ```

5. **Set up rsync from Pi:**
   See [INSTALL.md](INSTALL.md) for detailed instructions.

6. **Test the installation:**
   Open `http://your-server/` in a browser.

## 📁 Project Structure

```
remote_server/
├── public/              # Web root (Apache DocumentRoot)
│   ├── index.php       # Main dashboard
│   ├── api/            # RESTful API endpoints
│   ├── assets/         # CSS, JS files
│   ├── data/           # Synced data from Pi
│   └── .htaccess       # Apache config
├── config/
│   ├── database.php    # Database configuration
│   └── config.php      # Application settings
├── sql/
│   └── schema.sql      # MySQL database schema
├── scripts/
│   ├── sync_from_pi.sh # Rsync script
│   └── import_data.php # SQLite to MySQL importer
├── README.md           # This file
└── INSTALL.md          # Detailed installation guide
```

## 🔄 Data Synchronization

Data is synced from the Raspberry Pi using rsync over SSH:

1. **Database**: SQLite database is copied and imported to MySQL
2. **Photos**: Time-lapse and diary photos
3. **Videos**: Time-lapse videos

### Setting Up Automatic Sync

Add to crontab on the LAMP server:
```bash
*/5 * * * * /var/www/grow-tent/scripts/sync_from_pi.sh >> /var/log/grow-tent-sync.log 2>&1
```

## 🔌 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/current_data.php` | Latest sensor readings and stats |
| `GET /api/sensor_history.php` | Historical sensor data |
| `GET /api/projects.php` | List all projects |
| `GET /api/project.php?id=X` | Single project details |
| `GET /api/diary.php` | Diary entries |
| `GET /api/analysis.php` | AI analysis reports |
| `GET /api/timelapse.php` | Time-lapse videos/images |
| `GET /api/export.php` | Export data to CSV |

## 🔒 Security

- Optional HTTP Basic Authentication
- SQL injection prevention with prepared statements
- XSS protection headers
- CSRF protection for forms
- Directory listing disabled

To enable authentication:
1. Create `.htpasswd` file in the project root
2. Set `REQUIRE_AUTH` to `true` in `config/config.php`

## 🎨 Customization

### Changing Colors

Edit CSS variables in `public/assets/css/styles.css`:
```css
:root {
    --primary: #10b981;       /* Main accent color */
    --bg-dark: #0f172a;       /* Background color */
    --bg-card: #1e293b;       /* Card background */
}
```

### Auto-Refresh Interval

Edit in `config/config.php`:
```php
define('DASHBOARD_REFRESH_INTERVAL', 30);  // seconds
```

## 🐛 Troubleshooting

### No data showing
- Check if sync script ran successfully: `tail /var/log/grow-tent-sync.log`
- Verify MySQL connection settings
- Check file permissions on data directory

### Photos not loading
- Ensure rsync completed successfully
- Check Apache permissions on `public/data/`
- Verify image paths in database match actual files

### Charts not displaying
- Check browser console for JavaScript errors
- Ensure Chart.js CDN is accessible
- Verify API endpoints return valid JSON

## 📄 License

This project is part of the Grow Tent Automation System.

## 🙏 Credits

- [Chart.js](https://www.chartjs.org/) for charts
- Icons from emoji set
