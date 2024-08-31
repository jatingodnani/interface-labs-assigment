
from fastapi import FastAPI, File, UploadFile
import pandas as pd
import io
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/")
async def hello():
    return {"message": "Hello World"}

@app.post("/upload-1/")
async def upload_csv(file: UploadFile = File(...)):
    try:
        # Check if the uploaded file is a CSV or Excel file
        if file.content_type not in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            return {"error": "File must be a CSV or XLSX"}

        contents = await file.read()

        # Read the file into a DataFrame
        if file.content_type == "text/csv":
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        else:
            df = pd.read_excel(io.BytesIO(contents))

        if df.empty:
            return {"error": "Uploaded file is empty or not properly formatted"}

        # Process the DataFrame
        df = df[df["Transaction Type"] != "Cancel"]
        df["Transaction Type"] = df["Transaction Type"].replace({
            "Refund": "Return",
            "FreeReplacement": "Return"
        })
        df = df.fillna("")

       
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='ProcessedData')
        output.seek(0)

        
        
        headers = {
            'Content-Disposition': f'attachment; filename="{file.filename.split(".")[0]}_processed.xlsx"'
        }
        return StreamingResponse(output, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)

    except Exception as e:
        return {"error": str(e)} 








@app.post("/upload-2/")
async def upload_csv(file2: UploadFile = File(...)):
    try:
        # Check if the uploaded file is a CSV or Excel file
        if file2.content_type not in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            return {"error": "File must be a CSV or XLSX"}

        contents2 = await file2.read()
        print("File2 contents read successfully.")
        
        # Decode and clean the CSV data
        cleaned_data = contents2.decode("utf-8").replace('\r\n', '\n').replace('\r', '\n')
        
        # Create DataFrame from the cleaned CSV data
        df1 = pd.read_csv(io.StringIO(cleaned_data))

        # Debug: Print the initial DataFrame and its columns
        print("Initial DataFrame:\n", df1.head())
        print("DataFrame columns:", df1.columns)

        # Standardize column names
        df1.columns = df1.columns.str.strip().str.lower()

        # Check if 'total' column exists
        if 'total' not in df1.columns:
            raise ValueError("The 'total' column is missing from the DataFrame.")

        # Process the DataFrame
        if "type" in df1.columns:
            df1 = df1[df1["type"] != "Transfer"]
            df1 = df1.rename(columns={"type": "Payment Type"})
            print("Renamed columns:", df1.columns)

            
            print("Unique Payment Types before replacement:", df1["Payment Type"].unique())

            df1["Payment Type"] = df1["Payment Type"].replace({
                "Adjustment": "Order",
                "FBA Inventory Fee": "Order",
                "Fulfillment Fee": "Order",
                "Refund": "Order",
                "Service fee": "Order",
                "Refund": "Return"
            })

          
            df1['total'] = df1['total'].astype(str).str.replace(',', '').astype(float)

        else:
            print("Column 'type' not found in DataFrame.")

        df1["Transaction Type"] = "payment"
        df1 = df1.fillna("")

     
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df1.to_excel(writer, index=False, sheet_name='ProcessedData')
        
        output.seek(0)

       
        return StreamingResponse(output, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                 headers={"Content-Disposition": f"attachment; filename={file2.filename.split('.')[0]}_processed.xlsx"})

    except Exception as e:
        print("Error processing file:", e)
        return {"error": str(e)}
    




@app.post("/upload-both")
async def upload_both(file: UploadFile = File(...), file2: UploadFile = File(...)):
    try:
        # Check if both uploaded files are CSV or Excel files
        if file.content_type not in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"] or \
           file2.content_type not in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            return {"error": "Both files must be either CSV or XLSX"}

        # Read the first file into a DataFrame
        contents1 = await file.read()
        if file.content_type == "text/csv":
            df1 = pd.read_csv(io.StringIO(contents1.decode("utf-8")))
        else:
            df1 = pd.read_excel(io.BytesIO(contents1))

        # Read the second file into another DataFrame
        contents2 = await file2.read()
        if file2.content_type == "text/csv":
            df2 = pd.read_csv(io.StringIO(contents2.decode("utf-8")))
        else:
            df2 = pd.read_excel(io.BytesIO(contents2))

        if df1.empty or df2.empty:
            return {"error": "One of the uploaded files is empty or not properly formatted"}

        # Standardize column names
        df1.columns = df1.columns.str.strip().str.lower()
        df2.columns = df2.columns.str.strip().str.lower()

        # Process the first DataFrame (file1)
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
        else:
            return {"error": "'type' column not found in the first file"}
        
        df1["transaction type"] = "payment"

        # Process the second DataFrame (file2)
        if "transaction type" in df2.columns:
            df2 = df2[df2["transaction type"] != "Cancel"]
            df2["transaction type"] = df2["transaction type"].replace({
                "Refund": "Return",
                "freereplacement": "return"
            })
        else:
            return {"error": "'transaction type' column not found in the second file"}

        # Concatenate DataFrames by appending rows, ignoring any index
        merged_df = pd.concat([df1, df2], ignore_index=True)

        # Fill missing values with empty strings
        merged_df = merged_df.fillna("")

        # Save the merged DataFrame to an Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            merged_df.to_excel(writer, index=False, sheet_name='MergedData')
        output.seek(0)

        headers = {
            'Content-Disposition': 'attachment; filename="merged_processed.xlsx"'
        }
        return StreamingResponse(output, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)

    except Exception as e:
        print("Error processing files:", e)
        return {"error": str(e)}


