# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an agricultural AI agent system called "アグリAIエージェント" (Agri AI Agent) that provides intelligent farming assistance through LINE messaging. The system helps farmers with crop management, pest control, task scheduling, and agricultural decision-making by connecting to a MongoDB database and using LangChain for AI capabilities.

### Key Features
- LINE-based AI agent for agricultural consultations
- MongoDB database for crop, field, material, and work record management
- LangChain tools for intelligent farming recommendations
- Web dashboard for farm management
- Automated task scheduling and notifications
- Inventory and purchase order management

## Architecture

The system is designed with the following components:

### Core Technology Stack
- **Language**: Python 3.9+
- **AI Framework**: LangChain (Agent + Tools)
- **LLM**: OpenAI GPT-4 or Anthropic Claude
- **Database**: MongoDB Atlas (NoSQL)
- **Infrastructure**: Google Cloud Functions (Webhook), Google Cloud Run
- **Frontend**: Next.js + TypeScript + MUI (for dashboard)
- **Backend API**: FastAPI + Motor (async MongoDB)
- **Messaging**: LINE Messaging API
- **Authentication**: Firebase Auth with LINE OAuth
- **Secrets**: Google Secret Manager

### Database Design (MongoDB)
The system uses MongoDB with the following key collections:
- `crops`: Crop master data with cultivation calendars and disease/pest risks
- `materials`: Agricultural material master (pesticides, fertilizers)
- `fields`: Field master data with current cultivation status
- `cultivation_plans`: Annual crop rotation plans
- `work_records`: Historical work completion records
- `auto_tasks`: Future scheduled tasks
- `workers`: Worker master with LINE account linking
- `sensor_logs`: Sensor data logging
- `inventory`: Material inventory management
- `purchase_orders`: Purchase order management

### LangChain Tools
The system includes 11 primary tools (T1-T11):
- TaskLookupTool: Query pending tasks
- TaskUpdateTool: Update task completion status
- FieldInfoTool: Get field and cultivation information
- CropMaterialTool: Crop-material compatibility and dilution calculations
- InventoryCheckTool: Check material inventory
- WeatherForecastTool: Weather data retrieval
- And more for comprehensive farm management

## Development Phases

### Phase 0 - Foundation
- Environment setup (Next.js + FastAPI + MongoDB Atlas)
- LangChain agent foundation
- LINE Webhook foundation
- Authentication & read-only dashboard

### Phase 1 - Task Management & AI Core
- Tasks/Calendar CRUD implementation
- MongoDB Change Streams → LINE Push notifications
- Core LangChain tools implementation
- Work recommendation logic

### Phase 2 - Master Data Management
- Field, crop, material master CRUD UI
- Worker collection implementation & LINE ID linking

### Phase 3 - Inventory & Optimization
- Inventory & purchase order management
- AI agent performance optimization

### Phase 4 - Analytics & Security
- KPI/Analytics dashboard
- Security enhancements

### Phase 5 - Sensors & Automation
- Sensor data visualization
- Automated task generation

## Development Guidelines

### Language and Localization
- **All file updates, comments, and documentation should be written in Japanese**
- Code variable names and function names can be in English, but comments should be in Japanese
- User-facing messages and UI text must be in Japanese
- Error messages and logs should be in Japanese for better user support

### Working with MongoDB
- Use document-oriented design with embedded subdocuments
- Implement proper indexing for performance (field_code, work_date, etc.)
- Leverage MongoDB Change Streams for real-time updates
- Follow the schema defined in `docs/MongoDBデータベース設計.md`

### LangChain Integration
- All tools should connect to MongoDB collections
- Implement proper error handling and validation
- Tools should return structured data for LINE message formatting
- Performance target: <3 seconds response time

### LINE Integration
- Use LINE Messaging API for user interactions
- Implement signature verification for webhooks
- Support rich menus for common functions
- Handle both text and structured message responses

### Security Considerations
- Store API keys and secrets in Google Secret Manager
- Implement proper authentication and authorization
- Use rate limiting for API endpoints
- Log all user interactions for audit purposes

## Project Structure

```
docs/
├── MongoDBデータベース設計.md          # Complete database schema
├── 農業管理AIエージェント 要件定義書.md   # Comprehensive requirements
└── 開発タスクリスト.md                   # Development task list
```

## Key Documents

- **Database Design**: `docs/MongoDBデータベース設計.md` - Complete MongoDB schema with 13 collections
- **Requirements**: `docs/農業管理AIエージェント 要件定義書.md` - Detailed functional/non-functional requirements
- **Task List**: `docs/開発タスクリスト.md` - Development phases and task breakdown

## Performance Requirements

- AI agent response time: <3 seconds
- 24/7 system availability
- Support for scaling with farm size growth
- MongoDB Atlas redundancy for high availability

## Localization

The system is designed for Japanese agricultural operations with:
- Japanese language UI and messages
- JMA (Japan Meteorological Agency) weather integration
- Japanese agricultural standards and practices
- Japanese pesticide and fertilizer regulations