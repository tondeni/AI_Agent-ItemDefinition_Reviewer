import os
import json
import re
from docx import Document
from docx.enum.style import WD_STYLE_TYPE


# Helper: Load checklist from JSON
def load_checklist(plugin_folder):
    """
    Loads the compliance checklist from a JSON file saved in checklist folder.

    Args:
        plugin_folder (str): Path to the plugin folder.
    Returns:
        dict: Checklist data as a Python dictionary.
    Raises:
        FileNotFoundError: If the checklist file is not found.
        json.JSONDecodeError: If the JSON file has syntax errors.
    """
    checklist_path = os.path.join(plugin_folder, "checklists", "item_definition_checklist.json")
    with open(checklist_path, "r") as f:
        return json.load(f)


# Helper: Load Item Definition from txt file
def load_item_definition(plugin_folder):
    """
    Loads the content of the Item Definition document from a `.txt` file located in the plugin's 'item_definitions' directory.
    This function reads and returns the full content of the file as a string, which can be used by the LLM to perform a compliance review.

    Args:
        plugin_folder (str): The file system path to the root of the plugin folder.
    Returns:
        str: The full text content of the item definition document.
    Raises:
        FileNotFoundError: If the item_definition.txt file does not exist at the expected location.
    """
    item_def_path = os.path.join(plugin_folder, "item_definitions", "item_definition.txt")
    with open(item_def_path, "r", encoding="utf-8") as f:
        return f.read()

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
    # The pattern matches content between pipes (|), including the separator line (e.g., |---|---|)
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

# Helper Function: Create a custom table style for Word documents
def create_table_style(doc):
    """
    Creates and returns a custom table style ('CustomTable') based on the built-in 'Table Grid' style.
    This ensures consistent formatting for all tables in the generated document,
    making them more readable and visually appealing compared to default styling.

    Args:
        doc (Document): A python-docx Document object to which the style will be added.

    Returns:
        TableStyle: The newly created custom table style.
    """
    # Access the document's styles collection
    styles = doc.styles

    # Create a new table style called "CustomTable"
    table_style = styles.add_style("CustomTable", WD_STYLE_TYPE.TABLE)

    # Set the base style to 'Table Grid' — a built-in style that provides clean borders
    # This makes our custom style inherit all formatting from 'Table Grid'
    table_style.base_style = styles["Table Grid"]

    # Return the new style so it can be applied to tables
    return table_style

# Helper Function: Add a structured checklist item as a table to a Word document
def add_item_to_doc(doc, item_block):
    """
    Adds a 6-row table for a single checklist item into a Word document.
    Each table represents one requirement from the ISO 26262 Part 3 checklist,
    and includes:
        - Item ID
        - Requirement description
        - ISO Clause reference
        - Review status (Pass / Fail / Partially Pass)
        - Comment or justification
        - Suggestion

    Args:
        doc (Document): python-docx Document object where the table will be added.
        item_block (dict): Dictionary containing the item data. Must include:
            - "ID" (str): Checklist item ID (e.g., ITEM_001)
            - "Requirement" (str): Description of the requirement
            - "Clause" (str): Reference to ISO 26262 clause
            - "Status" (str): Result of review (e.g., Pass, Fail)
            - "Comment" (str): Justification or evidence
            - "Suggestion" (str): Hints or suggestion to improve Item Definition section

    Returns:
        None: Modifies the document in-place
    """

    # Create a new table with 5 rows and 2 columns
    table = doc.add_table(rows=5, cols=2)

    # Apply built-in 'Table Grid' style for borders and basic formatting
    table.style = "Table Grid"

    # Fill in the table cells with structured item data
    # Row 0: Item ID
    table.rows[0].cells[0].text = "Item"
    table.rows[0].cells[1].text = item_block["ID"]

    # Row 1: Requirement description
    table.rows[1].cells[0].text = "Requirement"
    table.rows[1].cells[1].text = item_block["Requirement"]

    # Row 2: ISO Clause reference
    table.rows[2].cells[0].text = "ISO Clause"
    table.rows[2].cells[1].text = item_block["Clause"]

    # Row 3: Review result (Pass / Fail / etc.)
    table.rows[3].cells[0].text = "Result"
    table.rows[3].cells[1].text = item_block["Status"]

    # Row 4: Comment or justification
    table.rows[4].cells[0].text = "Comment"
    table.rows[4].cells[1].text = item_block["Comment"]

    # Row 5: Suggestions for improvement
    table.rows[5].cells[0].text = "Suggestion"
    table.rows[5].cells[1].text = item_block["Suggestion"]

    # Add an empty paragraph after the table to separate items visually
    p = doc.add_paragraph()

    # Set paragraph formatting:
    p.paragraph_format.space_after = 0     # Remove space after paragraph
    p.paragraph_format.line_spacing = 1.0   # Set line spacing to single