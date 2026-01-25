#!/usr/bin/env python3
"""
Script to re-apply changes after git pull using context-based pattern matching.
This script applies changes to AndroidManifest files and DEPS without relying on line numbers.
"""

import re
import sys
from pathlib import Path


class ChangeApplier:
    """Applies changes to files using context-based pattern matching."""
    
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.changes_applied = []
        self.errors = []
    
    def apply_deps_change(self, file_path):
        """Apply checkout_pgo_profiles change to DEPS file."""
        full_path = self.root_dir / file_path
        if not full_path.exists():
            self.errors.append(f"File not found: {file_path}")
            return False
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if change already exists
        if "'checkout_pgo_profiles': True," in content:
            return False
        
        # Find and replace
        pattern = r"('checkout_pgo_profiles':\s*)False,"
        replacement = r"\1True,"
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content == content:
            self.errors.append(f"Could not find pattern in {file_path}")
            return False
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        self.changes_applied.append(f"Updated {file_path}: checkout_pgo_profiles = True")
        return True
    
    def add_automotive_uses_feature(self, content):
        """Add automotive uses-feature after leanback or touchscreen."""
        # Check if already present
        if 'android.hardware.type.automotive' in content:
            return content, False
        
        # Pattern 1: After android.software.leanback
        pattern1 = r'(<uses-feature\s+android:name="android\.software\.leanback"\s+android:required="false"\s*/>)'
        replacement1 = r'\1\n    <uses-feature\n        android:name="android.hardware.type.automotive"\n        android:required="true" />'
        
        if re.search(pattern1, content):
            new_content = re.sub(pattern1, replacement1, content, count=1)
            return new_content, True
        
        # Pattern 2: After android.hardware.touchscreen (with required="false")
        pattern2 = r'(<uses-feature\s+android:name="android\.hardware\.touchscreen"\s+android:required="false"\s*/>)\s*\n\s*({%\s*block)'
        replacement2 = r'\1\n    <uses-feature\n        android:name="android.hardware.type.automotive"\n        android:required="true" />\n    \2'
        
        if re.search(pattern2, content):
            new_content = re.sub(pattern2, replacement2, content, count=1)
            return new_content, True
        
        # Pattern 3: After android.hardware.touchscreen (standalone, before comment or block)
        pattern3 = r'(<uses-feature\s+android:name="android\.hardware\.touchscreen"\s+android:required="false"\s*/>)\s*\n\s*(<!--|{%|$)'
        replacement3 = r'\1\n    <uses-feature\n        android:name="android.hardware.type.automotive"\n        android:required="true" />\n    \2'
        
        if re.search(pattern3, content):
            new_content = re.sub(pattern3, replacement3, content, count=1)
            return new_content, True
        
        return content, False
    
    def add_distraction_optimized_to_application(self, content):
        """Add distractionOptimized meta-data right after application opening tag."""
        # Check if already present in application (right after opening tag)
        if re.search(r'<application[^>]*>\s*\n\s*<meta-data\s+android:name="distractionOptimized"', content):
            return content, False
        
        # Pattern for android_webview: after application tag with use32bitAbi or multiArch
        pattern1 = r'(<application[^>]*>\s*\n\s*{%\s*if\s+force_32_bit[^}]*%}\s*\n\s*{%\s*endif\s*%}\s*\n\s*>)\s*\n\s*(<meta-data|{#)'
        if re.search(pattern1, content):
            replacement1 = r'\1\n        <meta-data\n            android:name="distractionOptimized"\n            android:value="true"/>\n        \2'
            new_content = re.sub(pattern1, replacement1, content, count=1)
            if new_content != content:
                return new_content, True
        
        # Pattern for chrome: after application tag with extra_application_attributes block
        pattern2 = r'(<application[^>]*>\s*\n\s*{%\s*block\s+extra_application_attributes\s*%}{%\s*endblock\s*%}\s*>\s*\n\s*)\s*\n\s*({%\s*if\s+channel|{%\s*block|<meta-data)'
        if re.search(pattern2, content):
            replacement2 = r'\1        <meta-data\n            android:name="distractionOptimized"\n            android:value="true"/>\n\n        \2'
            new_content = re.sub(pattern2, replacement2, content, count=1)
            if new_content != content:
                return new_content, True
        
        # Generic pattern: after application opening tag
        pattern3 = r'(<application[^>]*>\s*\n\s*)({%\s*if\s+channel|{%\s*block|{%\s*if\s+javaless_renderers|<meta-data|{#)'
        if re.search(pattern3, content):
            replacement3 = r'\1        <meta-data\n            android:name="distractionOptimized"\n            android:value="true"/>\n\n        \2'
            new_content = re.sub(pattern3, replacement3, content, count=1)
            if new_content != content:
                return new_content, True
        
        return content, False
    
    def add_distraction_optimized_to_activity(self, content, activity_name_pattern):
        """Add distractionOptimized meta-data inside a specific activity before closing tag."""
        # Check if already present in this activity
        activity_pattern = rf'(<activity[^>]*android:name="{activity_name_pattern}"[^>]*>.*?)(</activity>)'
        match = re.search(activity_pattern, content, re.DOTALL)
        if match:
            activity_content = match.group(1)
            if 'distractionOptimized' in activity_content:
                return content, False
            
            # For MainActivity: insert after opening tag, before intent-filter
            if 'MainActivity' in activity_name_pattern:
                insert_pattern = rf'(<activity[^>]*android:name="{activity_name_pattern}"[^>]*>\s*\n)(\s*<intent-filter)'
                replacement = r'\1                <meta-data\n                    android:name="distractionOptimized"\n                    android:value="true"/>\n\2'
                if re.search(insert_pattern, content):
                    new_content = re.sub(insert_pattern, replacement, content, count=1)
                    if new_content != content:
                        return new_content, True
            
            # For ChromeTabbedActivity: insert before closing tag, after property
            if 'ChromeTabbedActivity' in activity_name_pattern and 'Activity2' not in activity_name_pattern:
                insert_pattern = rf'(<activity[^>]*android:name="{activity_name_pattern}"[^>]*>.*?<property[^>]*android:name="android\.window\.PROPERTY_SUPPORTS_MULTI_INSTANCE_SYSTEM_UI"[^>]*android:value="true"\s*/>)\s*\n(\s*</activity>)'
                replacement = r'\1\n            <meta-data\n            android:name="distractionOptimized"\n            android:value="true"/>\n        \2'
                if re.search(insert_pattern, content, re.DOTALL):
                    new_content = re.sub(insert_pattern, replacement, content, count=1, flags=re.DOTALL)
                    if new_content != content:
                        return new_content, True
            
            # For ChromeTabbedActivity2: insert before closing tag, after extra_web_rendering_activity_definitions
            if 'ChromeTabbedActivity2' in activity_name_pattern:
                insert_pattern = rf'(<activity[^>]*android:name="{activity_name_pattern}"[^>]*>.*?{{{{\s*self\.extra_web_rendering_activity_definitions\(\)\s*}}}})\s*\n(\s*</activity>)'
                replacement = r'\1\n            <meta-data\n            android:name="distractionOptimized"\n            android:value="true"/>\n        \2'
                if re.search(insert_pattern, content, re.DOTALL):
                    new_content = re.sub(insert_pattern, replacement, content, count=1, flags=re.DOTALL)
                    if new_content != content:
                        return new_content, True
            
            # For LicenseActivity: insert after PRIMARY_PROFILE_CONTROLLED meta-data
            if 'LicenseActivity' in activity_name_pattern:
                insert_pattern = rf'(<activity[^>]*android:name="{activity_name_pattern}"[^>]*>.*?<meta-data\s+android:name="com\.android\.settings\.PRIMARY_PROFILE_CONTROLLED"\s+android:value="true"\s*/>\s*\n)(\s*</activity>)'
                replacement = r'\1                <meta-data\n                    android:name="distractionOptimized"\n                    android:value="true"/>\n            \2'
                if re.search(insert_pattern, content, re.DOTALL):
                    new_content = re.sub(insert_pattern, replacement, content, count=1, flags=re.DOTALL)
                    if new_content != content:
                        return new_content, True
            
            # Generic: insert before closing </activity> tag
            insert_pattern = rf'(<activity[^>]*android:name="{activity_name_pattern}"[^>]*>.*?)(\s*</activity>)'
            replacement = r'\1            <meta-data\n            android:name="distractionOptimized"\n            android:value="true"/>\n        \2'
            
            new_content = re.sub(insert_pattern, replacement, content, count=1, flags=re.DOTALL)
            if new_content != content:
                return new_content, True
        
        return content, False
    
    def add_distraction_optimized_after_activity_alias(self, content, alias_name_pattern):
        """Add distractionOptimized meta-data after a specific activity-alias closing tag."""
        # Check if already present after this alias
        pattern = rf'(</activity-alias[^>]*android:name="{alias_name_pattern}"[^>]*>)\s*\n\s*(<meta-data[^>]*android:name="distractionOptimized")'
        if re.search(pattern, content):
            return content, False
        
        # Insert after activity-alias closing tag
        insert_pattern = rf'(</activity-alias[^>]*android:name="{alias_name_pattern}"[^>]*>)\s*\n\s*(<meta-data|</application|$)'
        replacement = r'\1\n    <meta-data\n            android:name="distractionOptimized"\n            android:value="true"/>\n    \2'
        
        if re.search(insert_pattern, content):
            new_content = re.sub(insert_pattern, replacement, content, count=1)
            return new_content, True
        
        return content, False
    
    def add_distraction_optimized_after_meta_data(self, content, after_meta_data_pattern):
        """Add distractionOptimized meta-data after a specific meta-data entry."""
        # Check if already present
        pattern = rf'({after_meta_data_pattern})\s*\n\s*(<meta-data[^>]*android:name="distractionOptimized")'
        if re.search(pattern, content):
            return content, False
        
        # Insert after the specified meta-data
        insert_pattern = rf'({after_meta_data_pattern})\s*\n\s*(<meta-data|</activity|</activity-alias|$)'
        replacement = r'\1\n                <meta-data\n                    android:name="distractionOptimized"\n                    android:value="true"/>\n            \2'
        
        if re.search(insert_pattern, content):
            new_content = re.sub(insert_pattern, replacement, content, count=1)
            return new_content, True
        
        return content, False
    
    def apply_android_manifest_changes(self, file_path, changes_config):
        """Apply all changes to an AndroidManifest file."""
        full_path = self.root_dir / file_path
        if not full_path.exists():
            self.errors.append(f"File not found: {file_path}")
            return False
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        any_changes = False
        
        # Add automotive uses-feature
        if changes_config.get('add_automotive_feature', False):
            content, changed = self.add_automotive_uses_feature(content)
            if changed:
                any_changes = True
        
        # Add distractionOptimized to application
        if changes_config.get('add_to_application', False):
            content, changed = self.add_distraction_optimized_to_application(content)
            if changed:
                any_changes = True
        
        # Add distractionOptimized to specific activities (process in reverse to avoid conflicts)
        for activity_name in reversed(changes_config.get('activities', [])):
            content, changed = self.add_distraction_optimized_to_activity(content, re.escape(activity_name))
            if changed:
                any_changes = True
        
        # Add distractionOptimized after activity-aliases
        for alias_name in changes_config.get('activity_aliases', []):
            content, changed = self.add_distraction_optimized_after_activity_alias(content, re.escape(alias_name))
            if changed:
                any_changes = True
        
        # Add distractionOptimized after specific meta-data
        for meta_data_pattern in changes_config.get('after_meta_data', []):
            content, changed = self.add_distraction_optimized_after_meta_data(content, meta_data_pattern)
            if changed:
                any_changes = True
        
        # Add distractionOptimized after activity closing (generic)
        for activity_pattern in changes_config.get('after_activities', []):
            # Find activity closing tag and add meta-data after it
            pattern = rf'({activity_pattern})\s*\n\s*(<meta-data|</application|$)'
            if not re.search(rf'{pattern}.*?distractionOptimized', content, re.DOTALL):
                replacement = r'\1\n                <meta-data\n                    android:name="distractionOptimized"\n                    android:value="true"/>\n            \2'
                new_content = re.sub(pattern, replacement, content, count=1)
                if new_content != content:
                    content = new_content
                    any_changes = True
        
        if any_changes:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.changes_applied.append(f"Updated {file_path}")
            return True
        
        return False
    
    def apply_expectation_file_changes(self, file_path):
        """Apply changes to expectation files (simpler pattern matching)."""
        full_path = self.root_dir / file_path
        if not full_path.exists():
            self.errors.append(f"File not found: {file_path}")
            return False
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        any_changes = False
        
        # Pattern 1: Add after application opening (for files with multiArch="true" or use32bitAbi="true")
        # Check if not already present
        pattern1 = r'(<application[^>]*(?:android:multiArch="true"|android:use32bitAbi="true")[^>]*>)\s*\n\s*(<activity|    <activity)'
        match1 = re.search(pattern1, content)
        if match1 and 'distractionOptimized' not in content[:match1.end() + 200]:
            replacement1 = r'\1\n    <meta-data\n        android:name="distractionOptimized"\n        android:value="true"/>\n    \2'
            new_content = re.sub(pattern1, replacement1, content, count=1)
            if new_content != content:
                content = new_content
                any_changes = True
        
        # Pattern 2: Add after activity closing (GoogleApiActivity) - for system_webview_32_64_bundle
        pattern2 = r'(</activity>\s*#\s*DIFF-ANCHOR:\s*ea1a94af)\s*\n\s*(<activity)'
        if re.search(pattern2, content) and not re.search(r'</activity>\s*#\s*DIFF-ANCHOR:\s*ea1a94af.*?distractionOptimized', content, re.DOTALL):
            replacement2 = r'\1\n        <meta-data\n            android:name="distractionOptimized"\n            android:value="true"/>\n    \2'
            new_content = re.sub(pattern2, replacement2, content, count=1)
            if new_content != content:
                content = new_content
                any_changes = True
        
        # Pattern 3: Add inside MainActivity (before intent-filter) - for system_webview_32_64_bundle
        pattern3 = r'(android:windowSoftInputMode="adjustPan">)\s*\n\s*(<intent-filter)'
        if re.search(pattern3, content) and not re.search(r'android:windowSoftInputMode="adjustPan">.*?distractionOptimized.*?<intent-filter', content, re.DOTALL):
            replacement3 = r'\1\n      <meta-data\n          android:name="distractionOptimized"\n          android:value="true"/>\n      \2'
            new_content = re.sub(pattern3, replacement3, content, count=1)
            if new_content != content:
                content = new_content
                any_changes = True
        
        # Pattern 4: Add after PRIMARY_PROFILE_CONTROLLED meta-data - for system_webview_32_64_bundle
        pattern4 = r'(<meta-data\s+android:name="com\.android\.settings\.PRIMARY_PROFILE_CONTROLLED"\s+android:value="true"/>)\s*\n\s*(</activity)'
        if re.search(pattern4, content) and not re.search(r'PRIMARY_PROFILE_CONTROLLED.*?distractionOptimized', content, re.DOTALL):
            replacement4 = r'\1\n      <meta-data\n          android:name="distractionOptimized"\n          android:value="true"/>\n    \2'
            new_content = re.sub(pattern4, replacement4, content, count=1)
            if new_content != content:
                content = new_content
                any_changes = True
        
        # Pattern 5: Add after activity-alias closing (SafeModeState/DeveloperModeState) - for all files
        pattern5 = r'(</activity-alias[^>]*#\s*DIFF-ANCHOR:\s*b7cc06e9)\s*\n\s*(<meta-data[^>]*android:name="\$PACKAGE\.WebViewLibrary")'
        if re.search(pattern5, content) and not re.search(r'DIFF-ANCHOR:\s*b7cc06e9.*?distractionOptimized.*?WebViewLibrary', content, re.DOTALL):
            replacement5 = r'\1\n    <meta-data\n            android:name="distractionOptimized"\n            android:value="true"/>\n    \2'
            new_content = re.sub(pattern5, replacement5, content, count=1)
            if new_content != content:
                content = new_content
                any_changes = True
        
        # Pattern 6: Add after activity-alias (for system_webview_bundle with visibleToInstantApps)
        pattern6 = r'(</activity-alias[^>]*android:visibleToInstantApps="true">\s*#\s*DIFF-ANCHOR:\s*b7cc06e9)\s*\n\s*(<meta-data[^>]*android:name="\$PACKAGE\.WebViewLibrary")'
        if re.search(pattern6, content) and not re.search(r'visibleToInstantApps="true">.*?DIFF-ANCHOR:\s*b7cc06e9.*?distractionOptimized', content, re.DOTALL):
            replacement6 = r'\1\n    <meta-data\n        android:name="distractionOptimized"\n        android:value="true"/>\n    \2'
            new_content = re.sub(pattern6, replacement6, content, count=1)
            if new_content != content:
                content = new_content
                any_changes = True
        
        if any_changes:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.changes_applied.append(f"Updated {file_path}")
            return True
        
        return False
    
    def run(self):
        """Apply all changes to all files."""
        # Define all files and their change configurations
        files_to_process = [
            {
                'path': 'DEPS',
                'type': 'deps',
            },
            {
                'path': 'android_webview/nonembedded/java/AndroidManifest.xml',
                'type': 'manifest',
                'config': {
                    'add_automotive_feature': True,
                    'add_to_application': True,
                    'activities': [
                        'org.chromium.android_webview.devui.MainActivity',
                        'org.chromium.android_webview.nonembedded.LicenseActivity',
                    ],
                },
            },
            {
                'path': 'chrome/android/java/AndroidManifest.xml',
                'type': 'manifest',
                'config': {
                    'add_automotive_feature': True,
                    'add_to_application': True,
                    'activities': [
                        'org.chromium.chrome.browser.ChromeTabbedActivity',
                        'org.chromium.chrome.browser.ChromeTabbedActivity2',
                    ],
                    'activity_aliases': [
                        'org.chromium.chrome.browser.ChromeTabbedActivityAlias',
                    ],
                },
            },
            {
                'path': 'chrome/android/java/AndroidManifest_trichrome_library.xml',
                'type': 'manifest',
                'config': {
                    'add_automotive_feature': True,
                },
            },
            {
                'path': 'android_webview/expectations/system_webview_32_64_bundle.AndroidManifest.expected',
                'type': 'expectation',
            },
            {
                'path': 'android_webview/expectations/system_webview_32_bundle.AndroidManifest.expected',
                'type': 'expectation',
            },
            {
                'path': 'android_webview/expectations/system_webview_64_32_bundle.AndroidManifest.expected',
                'type': 'expectation',
            },
            {
                'path': 'android_webview/expectations/system_webview_64_bundle.AndroidManifest.expected',
                'type': 'expectation',
            },
            {
                'path': 'android_webview/expectations/system_webview_bundle.AndroidManifest.expected',
                'type': 'expectation',
            },
        ]
        
        for file_info in files_to_process:
            file_path = file_info['path']
            file_type = file_info['type']
            
            if file_type == 'deps':
                self.apply_deps_change(file_path)
            elif file_type == 'manifest':
                self.apply_android_manifest_changes(file_path, file_info.get('config', {}))
            elif file_type == 'expectation':
                self.apply_expectation_file_changes(file_path)
        
        # Print results
        print("=" * 60)
        print("Change Application Results")
        print("=" * 60)
        
        if self.changes_applied:
            print(f"\n✓ Applied {len(self.changes_applied)} change(s):")
            for change in self.changes_applied:
                print(f"  - {change}")
        else:
            print("\n✓ No changes needed (all changes already applied)")
        
        if self.errors:
            print(f"\n✗ {len(self.errors)} error(s):")
            for error in self.errors:
                print(f"  - {error}")
        
        return len(self.errors) == 0


def main():
    """Main entry point."""
    root_dir = Path(__file__).parent
    applier = ChangeApplier(root_dir)
    success = applier.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
