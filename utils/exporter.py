import pandas as pd
from pathlib import Path

def export_to_excel(data: list[dict], dest_path: str, sheet_name: str = "Report") -> tuple[bool, str]:
    """
    Exports a list of dictionaries to an Excel spreadsheet.
    Returns (success, message).
    """
    try:
        if not data:
            return False, "No data available to export."
            
        df = pd.DataFrame(data)
        
        # Format column names to be human readable (e.g. 'student_id' -> 'Student ID')
        df.columns = [col.replace("_", " ").title() for col in df.columns]
        
        # Ensure parent folder exists
        file_path = Path(dest_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to Excel
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Auto-fit columns
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 10)
                
        return True, f"Report exported successfully to: {file_path.name}"
    except Exception as e:
        return False, f"Failed to export Excel: {str(e)}"
