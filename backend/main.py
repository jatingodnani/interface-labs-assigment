from fastapi import FastAPI, File, UploadFile
import pandas as pd
import io
import numpy as np

app = FastAPI()
@app.get("/")
async def hello():
    return {"message": "Hello World"}
@app.post("/upload-csv-excel/")
async def upload_csv(file: UploadFile = File(...),file2: UploadFile = File(...)):
    for file in [file,file2]:
        if file.content_type not in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            print("Uploaded file is not a CSV or XLSX") 
            return {"error": "File must be a CSV or XLSX"}


    contents = await file.read()
    print("File 1 contents read successfully.")
    print(contents)

    try:
        if file.content_type=="text/csv":
           df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
           print("DataFrame created from CSV:")
        else:

           df = pd.read_excel(io.BytesIO(contents))
           print("DataFrame created from EXCEL:")
        df = df[df["Transaction Type"] != "Cancel"]
        df["Transaction Type"]= df["Transaction Type"].replace({
            "Refund": "Return",
            "FreeReplacement": "Return"
        })

        df = df.fillna("")

        result = {
            "filename": file.filename,
            "columns": df.columns.tolist(),
            "data": df.to_dict(orient="records"),
        }

        # Print the result to server console
        print("Result prepared for response:")
        print(result)

        

    except Exception as e:
        print("Error processing CSV file:", e)  
        return {"error": str(e)}
    
    contents2=await file2.read();
    print("File2 contents read successfully.")
    print(contents2)

    try:
        if file2.content_type=="text/csv":
           df1 = pd.read_csv(io.StringIO(contents2.decode("utf-8")))
           print("DataFrame created from CSV:")
        else:

           df1 = pd.read_excel(io.BytesIO(contents2))
           print("DataFrame created from EXCEL:")
        df1 = df1[df1["type"] != "Transfer"]
        df1=df1.rename(columns={"type":"Payment Type"})
        df1["Payment Type"]= df1["Payment Type"].replace({
            "Adjustment":"Order",
            "FBA Inventory Fee":"Order",
            "Fulfillment Fee":"Order",
            "Refund":"Order",
            "Service fee":"Order",
             "Refund": "Return"
        })

        df1["Transaction Type"]="payment"
        df1 = df1.fillna("")
        return {
        "filename": file2.filename,
        "columns": df1.columns.tolist(),
        "data": df1.to_dict(orient="records")
    }
    except Exception as e:
        print("Error processing CSV file:", e)
        return {"error": str(e)}
