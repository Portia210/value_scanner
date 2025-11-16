from enum import Enum
import re
import os
import pandas as pd

enums_folder = "enums/"
if not os.path.exists(enums_folder):
    os.remove(enums_folder)
    os.makedirs(enums_folder)

def camel_string(s):
    """Convert string to CamelCase"""
    return ''.join(word.capitalize() for word in s.split('_'))
    

def save_enum_from_df(csv_path):
    """Generate Python Enum file from DataFrame with actual index values"""
    
    # get base name and remove extension
    report_name = re.search(r'([^/]+)\.csv$', csv_path).group(1).replace('-', '_')
    report_cameled_name = camel_string(report_name)
    
    # Get the corresponding .py filename
    py_filename = f"{report_name}_index.py"
    py_filepath = os.path.join(enums_folder, py_filename)
    df = pd.read_csv(csv_path, index_col=0)
    
    lines = [f"from enum import Enum\n\nclass {report_cameled_name}Index(Enum):"]
    
    for index_value in df.index:
        # Convert to valid Python identifier
        attr_name = str(index_value).upper()
        
        # Check if it contains (%)
        has_percent = '(%)' in attr_name
        
        # Remove only the parentheses, keep content inside
        attr_name = attr_name.replace('(', '').replace(')', '')
        
        # Replace & with _AND_
        attr_name = attr_name.replace('&', '_AND_')
        
        # Replace special chars with underscore
        attr_name = re.sub(r'[^A-Z0-9_]', '_', attr_name)  # Replace non-alphanumeric with _
        attr_name = re.sub(r'_+', '_', attr_name)  # Replace multiple _ with single _
        attr_name = attr_name.strip('_')  # Remove leading/trailing _
        
        # Add _PERCENT suffix if it had (%)
        if has_percent:
            # Remove existing _% or _PERCENT if any
            attr_name = re.sub(r'_PERCENT$', '', attr_name)
            attr_name = re.sub(r'_%$', '', attr_name)
            attr_name = attr_name + '_PERCENT'
        
        lines.append(f'    {attr_name} = "{index_value}"')
    
    code = '\n'.join(lines)
    
    with open(py_filepath, 'w') as f:
        f.write(code)
    
    print(f"Generated enum file: {py_filepath}")



if __name__ == "__main__":
    nvda_csv_files = os.listdir("data/NVDA/")
    for file in nvda_csv_files:
        full_path = os.path.join("data/NVDA/", file)
        if full_path.endswith(".csv"):
            save_enum_from_df(full_path)