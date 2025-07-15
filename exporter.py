import pandas as pd
from io import BytesIO, StringIO
from flask import Response, send_file
from datetime import datetime

def export_data(df, export_format, filename_prefix="ebay_products"):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return Response("No data available", status=404)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.{export_format}"

    if export_format == 'csv':
        output = StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return Response(
            output,
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    elif export_format == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Products')
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    elif export_format == 'json':
        output = df.to_json(orient='records', indent=2)
        return Response(
            output,
            mimetype='application/json',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    else:
        return Response("Invalid export format", status=400)