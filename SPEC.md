# IP Checker Telegram Bot Specification

## Project Overview
- **Project name**: IP Checker Bot
- **Type**: Telegram Bot
- **Core functionality**: A Telegram bot that responds to /start and allows users to send IP addresses to get detailed information including location, coordinates, and network provider
- **Target users**: Anyone wanting to check IP address details

## Functionality Specification

### Core Features
1. **/start command**: Welcome message with instructions
2. **IP lookup**: Accept IP addresses and return detailed information
3. **IP information to fetch**:
   - IP address
   - Country
   - Region/State
   - City
   - ISP (Internet Service Provider)
   - Organization
   - AS number
   - Latitude/Longitude coordinates
   - Timezone
   - Country code

### User Interactions
1. User sends /start → Bot responds with welcome message
2. User sends IP address → Bot responds with IP details in formatted message
3. Invalid input → Bot shows error message with instructions

### API
- Use ip-api.com (free tier, no API key required)
- Endpoint: http://ip-api.com/json/{ip}

## Technical Stack
- Python 3
- python-telegram-bot library
- GitHub Actions for deployment

## GitHub Actions Workflow
- Workflow to deploy bot to a free hosting service (Railway/Render/Fly.io)
- Or run locally for development

## Acceptance Criteria
1. Bot responds to /start with welcome message
2. Bot correctly parses and validates IP addresses
3. Bot fetches and displays all available IP details
4. Bot handles invalid IPs gracefully
5. Bot works with both IPv4 and IPv6