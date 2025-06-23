from cat.mad_hatter.decorators import tool
import os
import json


# Tool: Trigger the review process
@tool(return_direct=True)
def review_item_definition(tool_input, cat):
    """
    Reviews an Item Definition document using the ISO 26262 Part 3 checklist.
    
    This tool performs the following:
        - Loads a structured compliance checklist from JSON
        - Loads the item definition text file
        - Constructs a prompt for the LLM to analyze compliance
        - Sends the prompt to the LLM and returns the result directly to the user
    
    Args:
        tool_input (str): Input from the user (unused in this implementation)
        cat (Cat): Cheshire Cat instance, used to access memory and call the LLM

    Returns:
        str: LLM-generated table with compliance review results
             Includes: ID, Requirement, Status, Comment
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
- Status (Pass / Fail / Not Applicable)
- Comment

Be specific about what evidence supports your conclusion — refer to sections or descriptions in the Item Definition.

Return only the table — no extra explanation needed.
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