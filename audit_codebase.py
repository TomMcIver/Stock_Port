"""Audit codebase for unused files and cleanup opportunities"""

import os
import ast
import logging
from pathlib import Path
from typing import Set, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_python_files(root_dir: str = ".") -> List[Path]:
    """Find all Python files in the project"""
    python_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    return python_files

def extract_imports(file_path: Path) -> Set[str]:
    """Extract all imports from a Python file"""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
                    for alias in node.names:
                        imports.add(f"{node.module}.{alias.name}")
    except Exception as e:
        logger.debug(f"Error parsing {file_path}: {e}")
    
    return imports

def analyze_main_executables() -> Dict[str, str]:
    """Identify main executable files and their purposes"""
    
    main_files = {
        # Working commands from NEWS_PIPELINE_COMMANDS.md
        "update_news.py": "✅ MAIN - Incremental news updates",
        "get_years_of_news.py": "✅ MAIN - Historical backfill (years)", 
        "get_real_news.py": "✅ MAIN - Current news crawler",
        "setup_news_db.py": "✅ MAIN - Database setup",
        "check_news.py": "✅ UTILITY - Check database status",
        
        # Analysis tools we created
        "analyze_database.py": "✅ UTILITY - Database analysis",
        "check_timezones.py": "✅ UTILITY - Timezone analysis",
        
        # Database core
        "src/db/__init__.py": "✅ CORE - Database manager", 
        "src/ingest/news/ticker_tagger.py": "✅ CORE - Used by main scripts",
    }
    
    return main_files

def identify_unused_files() -> Dict[str, str]:
    """Identify potentially unused files"""
    
    # Get all Python files
    all_files = find_python_files()
    main_files = analyze_main_executables()
    
    # Files that might be unused
    potentially_unused = {}
    
    for file_path in all_files:
        try:
            rel_path = str(file_path.relative_to(Path.cwd())).replace('\\', '/')
        except ValueError:
            # Handle absolute paths
            rel_path = str(file_path).replace('\\', '/')
        
        # Skip if it's a main file
        if any(main_file in rel_path for main_file in main_files.keys()):
            continue
            
        # Check if it looks unused
        if any(pattern in rel_path for pattern in [
            'test_', 'pages/', 'services/', 'app.py', 'run.py',
            'backfill_historical_news.py', 'backfill_news.py', 
            'incremental_news_update.py', 'get_fresh_news.py',
            'run_simple_crawl.py'
        ]):
            # Analyze why it might be unused
            if 'test_' in rel_path:
                potentially_unused[rel_path] = "❓ TEST - Development test file"
            elif 'pages/' in rel_path:
                potentially_unused[rel_path] = "❓ STREAMLIT - Old Streamlit UI (not used)"  
            elif 'services/' in rel_path:
                potentially_unused[rel_path] = "❓ SERVICE - Old service layer"
            elif rel_path in ['app.py', 'run.py']:
                potentially_unused[rel_path] = "❓ UI - Old Streamlit app"
            elif 'backfill_historical_news.py' == rel_path:
                potentially_unused[rel_path] = "❓ DUPLICATE - Replaced by get_years_of_news.py"
            elif 'backfill_news.py' == rel_path:
                potentially_unused[rel_path] = "❓ OLD - Older backfill version"
            elif 'incremental_news_update.py' == rel_path:
                potentially_unused[rel_path] = "❓ DUPLICATE - Replaced by update_news.py"
            elif 'get_fresh_news.py' == rel_path:
                potentially_unused[rel_path] = "❓ OLD - Older version"
            else:
                potentially_unused[rel_path] = "❓ UNKNOWN - Purpose unclear"
        
        # Check src/ modules that might be unused
        elif 'src/' in rel_path and not any(core in rel_path for core in ['__init__.py', 'ticker_tagger.py', 'db/']):
            potentially_unused[rel_path] = "❓ MODULE - Old pipeline module (may be unused)"
    
    return potentially_unused

def check_file_usage() -> Dict[str, List[str]]:
    """Check which files import which other files"""
    
    all_files = find_python_files()
    usage_map = {}
    
    for file_path in all_files:
        imports = extract_imports(file_path)
        rel_path = str(file_path.relative_to(Path.cwd())).replace('\\', '/')
        usage_map[rel_path] = []
        
        # Find local imports
        for imp in imports:
            if imp.startswith('src.') or imp.startswith('.'):
                usage_map[rel_path].append(imp)
    
    return usage_map

def main():
    """Run codebase audit"""
    
    logger.info("🔍 CODEBASE AUDIT - Finding unused files")
    logger.info("=" * 60)
    
    # Identify main working files
    main_files = analyze_main_executables()
    logger.info("✅ MAIN WORKING FILES:")
    for file, purpose in main_files.items():
        if os.path.exists(file):
            logger.info(f"  {file:<35} {purpose}")
        else:
            logger.info(f"  {file:<35} {purpose} (NOT FOUND)")
    
    logger.info(f"\n❓ POTENTIALLY UNUSED FILES:")
    unused_files = identify_unused_files()
    
    categories = {}
    for file, reason in unused_files.items():
        category = reason.split(' - ')[0]
        if category not in categories:
            categories[category] = []
        categories[category].append((file, reason))
    
    for category, files in categories.items():
        logger.info(f"\n  {category}:")
        for file, reason in files:
            logger.info(f"    {file:<40} {reason}")
    
    logger.info(f"\n📊 SUMMARY:")
    logger.info(f"  Main working files: {len(main_files)}")
    logger.info(f"  Potentially unused: {len(unused_files)}")
    logger.info(f"  Total Python files: {len(find_python_files())}")
    
    # Show what you can safely remove
    logger.info(f"\n🗑️  SAFE TO REMOVE:")
    safe_to_remove = [
        f for f, reason in unused_files.items() 
        if any(x in reason for x in ['TEST', 'STREAMLIT', 'OLD', 'DUPLICATE'])
    ]
    
    for file in safe_to_remove:
        logger.info(f"  {file}")
        
    logger.info(f"\n⚠️  INVESTIGATE FURTHER:")
    investigate = [
        f for f, reason in unused_files.items() 
        if 'MODULE' in reason or 'UNKNOWN' in reason
    ]
    
    for file in investigate:
        logger.info(f"  {file}")

if __name__ == '__main__':
    main()