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

# Tool: Trigger the review process
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
    item_definitions_folder = os.path.join(plugin_folder, "item_definition_to_review")
    
    # Check if item_definitions folder exists
    if not os.path.exists(item_definitions_folder):
        return "❌ Error: item_definition_to_review folder not found."
    
    # Step 1: Load checklist from JSON file
    # This contains all ISO 26262 Part 3 requirements as structured data
    checklist = load_checklist(plugin_folder)

    # Step 2: Load the actual Item Definition content from .txt file
    item_definition = load_item_definition(plugin_folder)
    
    # Step 3: Build the prompt for the LLM
    response = generate_individual_review(item_definition, checklist, cat)

    cat.working_memory["document_type"] = "item_definition_review"
    cat.working_memory["reviewed_item"] = "item under review"  # e.g., "BMS"
    return response 

# Helper Function: Generate individual review for a file
def generate_individual_review(content, checklist, cat):
    
    item_def_content = content
    checklist_rev = json.dumps(checklist, indent=2)
    
    prompt = f""" You are a Functional Safety expert reviewing an Item Definition according to ISO 26262 Part 3.
Use the following checklist "{checklist_rev}" to evaluate the provided Item Definition "{item_def_content}".
For each checklist item, determine if it was met or not


 Be specific about what evidence supports your conclusion — refer to sections or descriptions in the Item Definition.  
  
 For each checklist item, determine if it was met. Output the results by filling the following sections :
**ID:** [ID]  
**Category:** [Category Name]  
**Requirement:** [Requirement text]  
**Description:** [Description from checklist]  
**Status:** Pass / Fail / Not Applicable  
**Comment:** [Your assessment]  
**Hint for improvement:** [Suggestion]

After each of this sections, output your response in a way they are clearly divided by each other (e.g. inserting a blank line or a solid line between them)"""
    
    return cat.llm(prompt)

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

    # Get the plugin's root folder path
    plugin_folder = os.path.dirname(__file__)
    item_definitions_folder = os.path.join(plugin_folder, "item_definition_to_review")
    
    # Check if item_definitions folder exists
    if not os.path.exists(item_definitions_folder):
        return "❌ Error: item_definitions folder not found."
    
    # Find all supported files in the folder
    supported_extensions = ['.pdf', '.docx', '.txt']
    files_to_process = "False"

    for filename in os.listdir(item_definitions_folder):
        file_path = os.path.join(item_definitions_folder, filename)
        if os.path.isfile(file_path):
            _, ext = os.path.splitext(filename.lower())
            if ext in supported_extensions:
                files_to_process = "True"
    
    if not files_to_process:
        return "❌ No supported files found in item_definitions folder. Supported formats: .pdf, .docx, .txt"

    print(f"📄 Processing file: {filename}")    
    
    # Extract content based on file type
    content = extract_file_content(file_path, ext)
    print(f"📝 Extracted {len(content)} characters from {filename}")    
    if not content.strip():
        print(f"⚠️ Warning: {filename} appears to be empty or unreadable")
       
   
    return content