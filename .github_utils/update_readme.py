import json
import os
import re

def get_version(folder_path):
    """Scans for __version__ in python files within a cog directory."""
    # Allow indentation (for class attributes) and optional type annotations (e.g., __version__: Final[str] = "x.x.x")
    version_pattern = re.compile(r'^\s*__version__\s*(?::\s*[^=]*)?\s*=\s*[\'"]([^\'"]+)[\'"]', re.MULTILINE)
    
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        match = version_pattern.search(content)
                        if match:
                            return match.group(1)
                except Exception as e:
                    print(f"Failed to read {file_path}: {e}")
    return "N/A"

def generate_readme():
    # Since script is in .github_utils/, dirname(dirname()) points to repo root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readme_path = os.path.join(repo_root, "README.md")
    
    cogs = []
    missing_versions = []
    
    # Iterate through the root directory
    for item in sorted(os.listdir(repo_root)):
        # Skip hidden folders (.git, .github, .github_utils) and files
        if item.startswith('.'):
            continue
            
        folder_path = os.path.join(repo_root, item)
        if not os.path.isdir(folder_path):
            continue
            
        info_json_path = os.path.join(folder_path, "info.json")
        if not os.path.exists(info_json_path):
            continue
            
        # Extract metadata from info.json
        try:
            with open(info_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                name = data.get('name', item)
                short_desc = data.get('short', data.get('description', 'No description provided.'))
                
                # Author handling: check if it's a list or a single string - just in case yk
                author_raw = data.get('author', ["Unknown"])
                if isinstance(author_raw, list):
                    author = ", ".join(author_raw)
                else:
                    author = str(author_raw)
                    
        except Exception as e:
            print(f"Failed to parse info.json in {item}: {e}")
            continue
            
        version = get_version(folder_path)
        if version == "N/A":
            missing_versions.append(name)
        
        cogs.append({
            'name': name,
            'folder': item,
            'description': short_desc,
            'author': author,
            'version': version
        })

    # Build the Markdown table
    table_lines = [
        "| ⚙️ Cog | 📝 Description | 🧑‍💻 Author | 📌 Version |",
        "|:---|:---|:---|:---|"
    ]
    
    for cog in cogs:
        # Relative link to the folder makes the repo portable for forks :)
        cog_link = f"**[{cog['name']}](./{cog['folder']})**"
        desc = cog['description'].replace('\n', ' ')
        version_str = f"`v{cog['version']}`" if cog['version'] != "N/A" else "`N/A`"
        
        table_lines.append(f"| {cog_link} | {desc} | {cog['author']} | {version_str} |")
        
    table_content = "\n".join(table_lines)
    
    # Create README if it doesn't exist
    if not os.path.exists(readme_path):
        print(f"README.md not found. Creating template...")
        template = f"""
<!-- START_COGS_TABLE -->
<!-- END_COGS_TABLE -->
"""
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(template)
        print("README.md created with template.")
    
    # Read README and replace content between markers
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_text = f.read()
    except FileNotFoundError:
        print(f"Error: {readme_path} not found.")
        return

    start_marker = "<!-- START_COGS_TABLE -->"
    end_marker = "<!-- END_COGS_TABLE -->"
    
    # regex to find everything between markers and replace it
    pattern = re.compile(rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL)
    
    if start_marker in readme_text and end_marker in readme_text:
        new_text = pattern.sub(f"{start_marker}\n{table_content}\n{end_marker}", readme_text)
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        print("README updated successfully!")
        
        if missing_versions:
            print(f"\n{len(missing_versions)} cog(s) missing __version__: {', '.join(missing_versions)}")
            print("   Add `__version__ = \"x.x.x\"` to your cog class to fix this.")
    else:
        print(f"Error: Could not find markers {start_marker} and {end_marker} in README.md")

if __name__ == "__main__":
    generate_readme()
