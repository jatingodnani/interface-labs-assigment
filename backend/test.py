
from fastapi import FastAPI,UploadFile
import pandas as pd
import io
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine,types,text
import json
import numpy as np
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
app = FastAPI()

@app.get("/")
async def hello():
    return {"message": "Hello World"}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:hello%40post123@localhost/labsassigment"
engine = create_engine(DATABASE_URL)

@app.post("/upload-both")
async def upload_both(file: UploadFile = File(...), file2: UploadFile = File(...)):
    try:
        logger.info("Starting file upload and processing")

        # Check if both uploaded files are CSV or Excel files
        if file.content_type not in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"] or \
           file2.content_type not in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            logger.error("Invalid file types uploaded")
            return {"error": "Both files must be either CSV or XLSX"}

        # Read the first file (Payment Report) into a DataFrame
        contents1 = await file.read()
        if file.content_type == "text/csv":
            df1 = pd.read_csv(io.StringIO(contents1.decode("utf-8")))
        else:
            df1 = pd.read_excel(io.BytesIO(contents1))
        logger.info(f"Payment Report loaded. Shape: {df1.shape}")

        # Read the second file (MTR) into another DataFrame
        contents2 = await file2.read()
        if file2.content_type == "text/csv":
            df2 = pd.read_csv(io.StringIO(contents2.decode("utf-8")))
        else:
            df2 = pd.read_excel(io.BytesIO(contents2))
        logger.info(f"MTR Report loaded. Shape: {df2.shape}")

        if df1.empty or df2.empty:
            logger.error("One of the uploaded files is empty or not properly formatted")
            return {"error": "One of the uploaded files is empty or not properly formatted"}

        # Standardize column names
        df1.columns = df1.columns.str.strip().str.lower()
        df2.columns = df2.columns.str.strip().str.lower()

        # Process the Payment Report (df1)
        if "type" in df1.columns:
            df1 = df1[df1["type"] != "transfer"]
            df1 = df1.rename(columns={"type": "payment type"})
            df1["payment type"] = df1["payment type"].replace({
                "adjustment": "order",
                "fba inventory fee": "order",
                "fulfillment fee": "order",
                "refund": "order",
                "service fee": "order",
                "refund": "return"
            })
            df1["transaction type"] = "payment"
        else:
            logger.error("'type' column not found in the Payment Report")
            return {"error": "'type' column not found in the Payment Report"}

        # Process the MTR Report (df2)
        if "transaction type" in df2.columns:
            df2 = df2[df2["transaction type"] != "Cancel"]
            df2["transaction type"] = df2["transaction type"].replace({
                "Refund": "Return",
                "free replacement": "return"
            })
        else:
            logger.error("'transaction type' column not found in the MTR Report")
            return {"error": "'transaction type' column not found in the MTR Report"}

        # Merge the DataFrames
        merged_df = pd.concat([df1, df2], ignore_index=True)
        logger.info(f"Merged dataframe shape: {merged_df.shape}")

        # Clean the data
        merged_df = merged_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        numeric_columns = ["total", "invoice amount"]
        for column in numeric_columns:
            if column in merged_df.columns:
                merged_df[column] = pd.to_numeric(merged_df[column].replace({r',': ''}, regex=True), errors='coerce')

        # Handle empty Order IDs
        empty_order_summary = merged_df[merged_df['order id'].isna() | (merged_df['order id'] == '')].groupby('description')['total'].sum().reset_index()
        logger.info(f"Empty Order ID summary: {empty_order_summary.to_dict(orient='records')}")

        # Categorize the data
        def categorize(row):
            if pd.isna(row['order id']) or row['order id'] == '':
                return 'Empty Order ID'
            elif len(str(row['order id'])) == 10:
                return 'Removal Order IDs'
            elif row['transaction type'] == 'Return' and not pd.isna(row['invoice amount']):
                return 'Return'
            elif row['transaction type'] == 'Payment' and row['total'] < 0:
                return 'Negative Payout'
            elif not pd.isna(row['total']) and not pd.isna(row['invoice amount']):
                return 'Order & Payment Received'
            elif not pd.isna(row['total']) and pd.isna(row['invoice amount']):
                return 'Order Not Applicable but Payment Received'
            elif pd.isna(row['total']) and not pd.isna(row['invoice amount']):
                return 'Payment Pending'
            else:
                return 'Uncategorized'

        merged_df['category'] = merged_df.apply(categorize, axis=1)
        category_summary = merged_df['category'].value_counts()
        logger.info(f"Category summary: {category_summary.to_dict()}")

        # Calculate tolerance status
        def calculate_tolerance(row):
            if pd.isna(row['total']) or pd.isna(row['invoice amount']) or row['invoice amount'] == 0:
                return 'N/A'
            ratio = (row['total'] / row['invoice amount']) * 100
            pna = row['total']
            if 0 < pna <= 300 and ratio > 50:
                return 'Within Tolerance'
            elif 300 < pna <= 500 and ratio > 45:
                return 'Within Tolerance'
            elif 500 < pna <= 900 and ratio > 43:
                return 'Within Tolerance'
            elif 900 < pna <= 1500 and ratio > 38:
                return 'Within Tolerance'
            elif pna > 1500 and ratio > 30:
                return 'Within Tolerance'
            else:
                return 'Tolerance Breached'

        merged_df['tolerance_status'] = merged_df.apply(calculate_tolerance, axis=1)
        
        # Create summary data with tolerance breakdown
        summary_data = []
        for category in category_summary.index:
            category_df = merged_df[merged_df['category'] == category]
            tolerance_counts = category_df['tolerance_status'].value_counts()
            
            summary_data.append({
                'category': category,
                'count': category_summary[category],
                'tolerance_within': tolerance_counts.get('Within Tolerance', 0),
                'tolerance_breached': tolerance_counts.get('Tolerance Breached', 0),
                'tolerance_na': tolerance_counts.get('N/A', 0)
            })

        summary_df = pd.DataFrame(summary_data)

        # Add a total row
        total_row = pd.DataFrame({
            'category': ['Total'],
            'count': [summary_df['count'].sum()],
            'tolerance_within': [summary_df['tolerance_within'].sum()],
            'tolerance_breached': [summary_df['tolerance_breached'].sum()],
            'tolerance_na': [summary_df['tolerance_na'].sum()]
        })
        summary_df = pd.concat([summary_df, total_row], ignore_index=True)

        # Prepare data for database insertion
        columns_to_insert = ["order id", "transaction type", "payment type", "invoice amount", "total", "description", "order date", "category", "tolerance_status"]
        df_to_insert = merged_df[columns_to_insert]

        # Define the SQLAlchemy types for the columns
        sql_dtypes = {
            'order id': types.Text(),
            'transaction type': types.Text(),
            'payment type': types.Text(),
            'invoice amount': types.Float(),
            'total': types.Float(),
            'description': types.Text(),
            'order date': types.DateTime(),
            'category': types.Text(),
            'tolerance_status': types.Text()
        }

        # Save the processed DataFrame to the database
        table_name = "processed_transactions"
        df_to_insert.to_sql(table_name, engine, if_exists='replace', index=False, dtype=sql_dtypes)
        logger.info(f"Successfully inserted {len(df_to_insert)} rows into the database")

        # Save the summary DataFrame to the database
        summary_table_name = "summary_table"
        summary_sql_dtypes = {
            'category': types.Text(),
            'count': types.Integer(),
            'tolerance_within': types.Integer(),
            'tolerance_breached': types.Integer(),
            'tolerance_na': types.Integer()
        }
        summary_df.to_sql(summary_table_name, engine, if_exists='replace', index=False, dtype=summary_sql_dtypes)
        logger.info(f"Successfully inserted {len(summary_df)} rows into the summary table")

        return JSONResponse(content={
            "message": f"Successfully processed {len(df_to_insert)} rows",
            "empty_order_summary": empty_order_summary.to_dict(orient='records'),
            "summary_table": summary_df.to_dict(orient='records')
        })

    except Exception as e:
        logger.error(f"Error processing files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/get-summary")
async def get_summary():
    try:
        logger.info("Fetching summary data from the database")
        query = "SELECT * FROM summary_table"
        df = pd.read_sql(query, engine)
        
        if df.empty:
            logger.warning("No summary data found in the database")
            return JSONResponse(content={"message": "No summary data available"}, status_code=404)
        
        summary_data = df.to_dict(orient='records')
        logger.info(f"Successfully retrieved {len(summary_data)} rows of summary data")
        return JSONResponse(content={"summary_data": summary_data})
    
    except Exception as e:
        logger.error(f"Error fetching summary data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
