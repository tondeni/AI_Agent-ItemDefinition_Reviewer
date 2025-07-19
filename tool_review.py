from cat.mad_hatter.decorators import tool
import os
import json
import zipfile
import csv
from io import BytesIO, StringIO
from datetime import datetime
import base64
from docx import Document as DocxDocument
from docx.shared import Pt
from docx.enum.style import WD_STYLE_TYPE
import PyPDF2
import re


# Tool: Batch review of multiple item definitions
@tool(return_direct=True)
def review_item_definitions_batch(tool_input, cat):
    """Review multiple item definition files against ISO 26262 compliance checklist.
    This tool processes all files in the item_definitions folder (.pdf, .docx, .txt)
    and generates individual review reports with CSV and DOCX outputs packaged in ZIP files.
    
    Args:
        tool_input: Input from the user (not used in this tool)
        cat: Cheshire Cat instance
    
    Returns:
        Summary of processed files and generated ZIP archives
    """

    print("✅ TOOL CALLED: review_item_definitions_batch")

    # Get the plugin's root folder path
    plugin_folder = os.path.dirname(__file__)
    item_definitions_folder = os.path.join(plugin_folder, "item_definitions")
    
    # Check if item_definitions folder exists
    if not os.path.exists(item_definitions_folder):
        return "❌ Error: item_definitions folder not found."
    
    # Find all supported files in the folder
    supported_extensions = ['.pdf', '.docx', '.txt']
    files_to_process = []
    
    for filename in os.listdir(item_definitions_folder):
        file_path = os.path.join(item_definitions_folder, filename)
        if os.path.isfile(file_path):
            _, ext = os.path.splitext(filename.lower())
            if ext in supported_extensions:
                files_to_process.append((filename, file_path, ext))
    
    if not files_to_process:
        return "❌ No supported files found in item_definitions folder. Supported formats: .pdf, .docx, .txt"
    
    print(f"🔍 Found {len(files_to_process)} files to process:")
    for filename, file_path, ext in files_to_process:
        print(f"  • {filename} ({ext})")
    
    # Load checklist once
    try:
        checklist = load_checklist(plugin_folder)
        print(f"📋 Checklist loaded successfully")
    except FileNotFoundError as e:
        return f"❌ Error loading checklist: {e}"
    
    # Process each file
    processed_files = []
    zip_files_created = []
    
    for filename, file_path, ext in files_to_process:
        try:
            print(f"📄 Processing file: {filename}")
            
            # Extract content based on file type
            content = extract_file_content(file_path, ext)
            print(f"📝 Extracted {len(content)} characters from {filename}")
            
            if not content.strip():
                print(f"⚠️ Warning: {filename} appears to be empty or unreadable")
                continue
            
            # Generate review for this file (bypass hook by setting flag)
            print(f"🤖 Generating review for {filename}...")
            cat._batch_processing = True
            review_result = generate_individual_review(content, checklist, cat)
            cat._batch_processing = False
            print(f"📊 Review generated for {filename}, length: {len(review_result)}")
            
            # Create ZIP package for this file
            print(f"📦 Creating ZIP package for {filename}...")
            zip_path = create_review_package(filename, review_result, checklist, plugin_folder)
            
            if zip_path:
                processed_files.append(filename)
                zip_files_created.append(zip_path)
                print(f"✅ Created review package: {os.path.basename(zip_path)}")
            else:
                print(f"❌ Failed to create ZIP package for {filename}")
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    # Generate summary response
    if processed_files:
        summary = f"✅ Successfully processed {len(processed_files)} file(s):\n\n"
        for i, filename in enumerate(processed_files):
            zip_name = os.path.basename(zip_files_created[i])
            summary += f"• {filename} → {zip_name}\n"
        
        summary += f"\n📁 All ZIP files saved in: {os.path.join(plugin_folder, 'exports')}\n"
        summary += "\nEach ZIP contains:\n• .csv file (Excel-compatible review data)\n• .docx file (Formatted review report)"
        
        return summary
    else:
        return "❌ No files were successfully processed. Please check the files and try again."


# Tool: Original single file review (kept for backward compatibility)
@tool(return_direct=True)
def review_item_definition(tool_input, cat):
    """Review the current item definition against ISO 26262 compliance checklist.
    This tool loads the item definition from the plugin folder and provides
    assessment results with specific suggestions for improvement.
    
    Args:
        tool_input: Input from the user (not used in this tool)
        cat: Cheshire Cat instance
    
    Returns:
        Assessment results with compliance score and improvement suggestions
    """

    # Print confirmation that the tool was triggered
    print("✅ TOOL CALLED: review_item_definition")

    # Get the plugin's root folder path
    plugin_folder = os.path.dirname(__file__)

    # Step 1: Load checklist from JSON file
    # This contains all ISO 26262 Part 3 requirements as structured data
    checklist = load_checklist(plugin_folder)

    # Step 2: Load the actual Item Definition content from .txt file
    item_definition = load_item_definition(plugin_folder)

    # Step 3: Build the prompt for the LLM
    prompt = f"""
You are a Functional Safety expert reviewing an Item Definition according to ISO 26262 Part 3.

Use the following checklist to evaluate the provided Item Definition:
{json.dumps(checklist, indent=2)}

Here is the actual Item Definition content:

"{item_definition}"

For each checklist item, determine if it was met. Output the results in a markdown-style table format with columns:
- ID
- Requirement
- Description
- Status (Pass / Fail / Not Applicable)
- Comment

Be specific about what evidence supports your conclusion — refer to sections or descriptions in the Item Definition.


"""

    # Step 4: Send prompt to LLM
    response = cat.llm(prompt)

    # Step 5: Return the LLM’s response directly to the user
    return response


# Helper Function: Load checklist from JSON file
def load_checklist(plugin_folder):
    """
    Loads the ISO 26262 Part 3 compliance checklist from a JSON file.
    This function constructs the path to the checklist file based on the plugin folder,
    then reads and parses the JSON content for use in the AI-based review process.

    Args:
        plugin_folder (str): The file system path to the root of the plugin folder.

    Returns:
        dict: A dictionary representing the parsed JSON checklist data.
        
    Raises:
        FileNotFoundError: If the checklist file is not found at the expected location.
    """

    # Construct the full path to the checklist JSON file
    checklist_path = os.path.join(plugin_folder, "checklists", "item_definition_checklist.json")

    try:
        # Open the JSON file in read mode
        with open(checklist_path, "r") as f:
            # Load and return the JSON data as a Python dictionary
            return json.load(f)
    
    except FileNotFoundError:
        # If the file doesn't exist, raise a descriptive error
        raise FileNotFoundError(f"Checklist file not found at {checklist_path}")


# Helper Function: Load Item Definition from text file
def load_item_definition(plugin_folder):
    """
    Loads the content of the Item Definition document from a `.txt` file located in the plugin's 'item_definitions' directory.
    This function reads and returns the full text content of the file, which can be used by the LLM to perform a compliance review.

    Args:
        plugin_folder (str): The file system path to the root of the plugin folder.

    Returns:
        str: The full text content of the item definition document.

    Raises:
        FileNotFoundError: If the item_definition.txt file does not exist at the expected location.
    """

    # Construct the full path to the item definition text file
    item_def_path = os.path.join(plugin_folder, "item_definitions", "item_definition.txt")

    try:
        # Open the file in read mode with UTF-8 encoding
        with open(item_def_path, "r", encoding="utf-8") as f:
            # Read and return the entire file content
            return f.read()

    except FileNotFoundError:
        # If the file doesn't exist, raise a descriptive error
        raise FileNotFoundError(f"Item Definition file not found at {item_def_path}")


# Helper Function: Extract content from different file types
def extract_file_content(file_path, file_extension):
    """
    Extracts text content from different file formats.
    
    Args:
        file_path (str): Path to the file
        file_extension (str): File extension (.pdf, .docx, .txt)
    
    Returns:
        str: Extracted text content
    """
    try:
        if file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif file_extension == '.pdf':
            content = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
            return content
        
        elif file_extension == '.docx':
            doc = DocxDocument(file_path)
            content = ""
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"
            return content
        
        else:
            return ""
    
    except Exception as e:
        print(f"Error extracting content from {file_path}: {str(e)}")
        return ""


# Helper Function: Generate individual review for a file
def generate_individual_review(content, checklist, cat):
    """
    Generates a review for individual file content using the LLM.
    
    Args:
        content (str): File content to review
        checklist (dict): Checklist data
        cat: Cheshire Cat instance
    
    Returns:
        str: LLM review response
    """
    prompt = f"""
You are a Functional Safety expert reviewing an Item Definition according to ISO 26262 Part 3.

Use the following checklist to evaluate the provided Item Definition:
{json.dumps(checklist, indent=2)}

Here is the actual Item Definition content:

"{content}"

For each checklist item, determine if it was met. Output the results in a markdown-style table format with columns:
- ID
- Requirement
- Description
- Status (Pass / Fail / Not Applicable)
- Comment

Be specific about what evidence supports your conclusion — refer to sections or descriptions in the Item Definition.

"""
    
    return cat.llm(prompt)


# Helper Function: Create review package (ZIP with CSV and DOCX)
def create_review_package(original_filename, review_result, checklist, plugin_folder):
    """
    Creates a ZIP package containing CSV and DOCX files for a single file review.
    
    Args:
        original_filename (str): Name of the original file being reviewed
        review_result (str): LLM review response
        checklist (dict): Checklist data
        plugin_folder (str): Plugin folder path
    
    Returns:
        str: Path to created ZIP file, or None if failed
    """
    try:
        # Parse the review result
        print(f"🔍 Parsing review result for {original_filename}...")
        print(f"📝 Review result preview (first 500 chars): {review_result[:500]}...")
        review_data = parse_markdown_table(review_result)
        print(f"📊 Parsed {len(review_data)} table rows for {original_filename}")
        
        if not review_data:
            print(f"❌ Warning: No table data found in review for {original_filename}")
            print(f"📄 Full review result: {review_result}")
            return None
        
        # Create unique timestamp and base filename for each file
        import time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{int(time.time() * 1000) % 10000:04d}"
        base_name = os.path.splitext(original_filename)[0]
        
        # Create DOCX document
        doc = DocxDocument()
        doc.add_heading(f'ISO 26262 Part 3 - Item Definition Review Report', level=1)
        doc.add_heading(f'File: {original_filename}', level=2)
        
        # Load checklist items for enrichment
        checklist_items = checklist.get("items", [])
        checklist_map = {item["id"]: item for item in checklist_items}
        
        # Group by category and add to document
        current_category = None
        for item in review_data:
            item_id = item.get("ID", "")
            checklist_item = checklist_map.get(item_id, {})
            category = checklist_item.get("category", "Uncategorized")
            
            # Add category heading if changed
            if current_category != category:
                doc.add_heading(category, level=3)
                current_category = category
            
            # Create table for this item
            table = doc.add_table(rows=5, cols=2)
            table.style = 'Table Grid'
            
            # Set column widths
            for row in table.rows:
                row.cells[0].width = Pt(2.5 * 1440 / 72)
                row.cells[1].width = Pt(20.0 * 1440 / 72)
            
            # Fill table content
            def set_cell_text(cell, text, bold=False):
                paragraph = cell.paragraphs[0]
                run = paragraph.add_run(text)
                run.bold = bold
                run.font.size = Pt(10)
            
            set_cell_text(table.rows[0].cells[0], "Requirement", bold=True)
            set_cell_text(table.rows[0].cells[1], checklist_item.get("requirement", ""))
            
            set_cell_text(table.rows[1].cells[0], "Description", bold=True)
            set_cell_text(table.rows[1].cells[1], checklist_item.get("description", "N/A"))
            
            set_cell_text(table.rows[2].cells[0], "ISO Clause", bold=True)
            set_cell_text(table.rows[2].cells[1], checklist_item.get("iso_clause", "N/A"))
            
            set_cell_text(table.rows[3].cells[0], "Result", bold=True)
            set_cell_text(table.rows[3].cells[1], item.get("Status", "Not Reviewed"))
            
            set_cell_text(table.rows[4].cells[0], "Comment", bold=True)
            set_cell_text(table.rows[4].cells[1], item.get("Comment", ""))
            
            # Add spacing
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
        
        # Save DOCX to buffer
        doc_buffer = BytesIO()
        doc.save(doc_buffer)
        doc_buffer.seek(0)
        doc_bytes = doc_buffer.getvalue()
        doc_buffer.close()
        
        # Create CSV content
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer, delimiter=";")
        csv_writer.writerow(["ID", "Requirement", "Description", "Clause", "Status", "Comment"])
        
        for item in review_data:
            item_id = item.get("ID", "")
            status = item.get("Status", "")
            comment = item.get("Comment", "")
            
            checklist_item = checklist_map.get(item_id, {})
            full_requirement = checklist_item.get("requirement", "")
            iso_clause = checklist_item.get("iso_clause", "N/A")
            description = checklist_item.get("description", "N/A")
            
            csv_writer.writerow([item_id, full_requirement, description, iso_clause, status, comment])
        
        csv_content = csv_buffer.getvalue()
        csv_buffer.close()
        
        # Create ZIP file
        exports_folder = os.path.join(plugin_folder, "exports")
        os.makedirs(exports_folder, exist_ok=True)
        
        zip_filename = f"{base_name}_review_{timestamp}.zip"
        zip_path = os.path.join(exports_folder, zip_filename)
        
        with zipfile.ZipFile(zip_path, "w") as zip_file:
            # Add DOCX file
            docx_filename = f"{base_name}_review_{timestamp}.docx"
            zip_file.writestr(docx_filename, doc_bytes)
            
            # Add CSV file
            csv_filename = f"{base_name}_review_{timestamp}.csv"
            zip_file.writestr(csv_filename, csv_content)
        
        return zip_path
    
    except Exception as e:
        print(f"Error creating review package for {original_filename}: {str(e)}")
        return None


# Helper Function: Parse markdown-style tables from text
def parse_markdown_table(text):
    """
    Parses markdown-style tables from a given text string and returns them as a list of dictionaries.
    
    Args:
        text (str): A string containing one or more markdown-style tables.
        
    Returns:
        List[Dict]: A list where each dictionary represents a row in the table,
                    with keys from the header row and values from the data rows.
                    
    """
    # Use regex to find all markdown-style tables in the input text
    table_pattern = re.compile(r"(\|.*\|\s*\|[-:]*[-|]\s*(?:\|.*\|[\s\d]*)+)", re.DOTALL)
    
    # Find all matches in the input text
    tables = table_pattern.findall(text)

    # Initialize an empty list to store parsed tables' data
    parsed_data = []

    # Loop through each matched table
    for table in tables:
        # Split the table into lines and strip whitespace
        lines = [line.strip() for line in table.strip().split('\n')]
        
        # Skip if there are not enough lines (header + separator + at least one data row)
        if len(lines) < 2:
            continue

        # Extract headers from the first line (remove empty cells from start and end using [1:-1])
        headers = [h.strip() for h in lines[0].split('|')[1:-1]]

        # Process each data row starting after the separator line (lines[2:])
        for line in lines[2:]:
            # Extract cells from the current line, stripping whitespace
            cells = [c.strip() for c in line.split('|')[1:-1]]
            
            # Skip empty rows
            if not any(cells):
                continue

            # Map headers to cell values and add to result list
            row = dict(zip(headers, cells))
            parsed_data.append(row)

    # Return the list of parsed rows
    return parsed_data