# FastAPI Data Processing Application

## Overview

This FastAPI application processes and merges two datasets: a Payment Report (CSV) and a Merchant Tax Report (MTR) (XLSX). It performs data cleaning, categorization, and tolerance checks, then stores the processed data and summaries in a PostgreSQL database. The application is Dockerized for easy deployment.

**Note:** A frontend application is planned but has not yet been added to the project.

## Setup Instructions

### Prerequisites

- **Docker**: Ensure Docker is installed on your machine. Follow [Docker's installation guide](https://docs.docker.com/get-docker/) if needed.
- **Docker Compose**: Install Docker Compose if it is not included with your Docker installation. Follow the [Docker Compose Installation guide](https://docs.docker.com/compose/install/).

### Running the Application Locally

1. **Clone the Repository**

   ```bash git clone <your-repository-url>
   cd <your-repository-directory>
Build and Start the Docker Containers



2. docker
docker-compose up --build
This command will build the Docker images and start the FastAPI application along with the PostgreSQL database.

Access the Application



**API Endpoints:**
## POST /upload-both-mtr-paymentfile: Upload and process CSV and Excel files.
### GET /get-summary: Retrieve the summary of processed data.
**Design Choices**
Database Schema
Tables:

## processed_transactions: Stores detailed records of transactions.
## summary_table: Contains summarized data and tolerance status.
## Data Types: Utilizes PostgreSQL data types that match the expected format of each column (e.g., Text, Float, DateTime).

**API Design**
# File Upload Endpoint (/upload-both-mtr-paymentfile): Accepts two files (CSV and XLSX), processes them, and stores the results in the database.
# Summary Endpoint (/get-summary): Provides a summary of the processed data from the summary_table.
**ELT Pipeline**
## Extract: Load data from the CSV and XLSX files.
## Transform: Clean and process data (e.g., renaming columns, filtering rows, merging datasets).
## Load: Insert the processed data and summaries into PostgreSQL tables.
**CI/CD Setup**
## Docker: Containerizes the FastAPI application and PostgreSQL database.
## Docker Compose: Manages multi-container deployment, including building and running the application.
**Frontend**
## A frontend application is planned to provide a user interface for interacting with the FastAPI application. However, it has not yet been developed or added to the project.

**Known Issues and Potential Improvements**
## Case Sensitivity Handling: The application currently has rigid case-sensitive handling for column values. Future improvements could include making the case handling more flexible to accommodate various data input formats.
## Error Handling: will try to improve the error handling

**Request for Review**
 ## I would appreciate any feedback or review on this project. Your insights will be valuable in evaluating the implementation and identifying areas for improvement.

**Thank you for your time and consideration!**
