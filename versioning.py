import streamlit as st
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Release Notes - LDT Decision Engine",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for styling ---
st.markdown("""
<style>
    .release-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1.5rem;
        color: #1f77b4;
    }
    .release-entry {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        border-left: 4px solid #1f77b4;
    }
    .release-date {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
    .release-version {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        margin-bottom: 0.5rem;
    }
    .release-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .badge-major {
        background-color: #dc3545;
        color: white;
    }
    .badge-minor {
        background-color: #ffc107;
        color: #333;
    }
    .badge-patch {
        background-color: #6c757d;
        color: white;
    }
    .badge-operational {
        background-color: #28a745;
        color: white;
    }
    .release-description {
        color: #444;
        line-height: 1.6;
        margin-top: 1rem;
    }
    .info-section {
        background-color: #e7f3ff;
        padding: 2rem;
        border-radius: 10px;
        margin-top: 3rem;
    }
    .info-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #0066cc;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown('<div class="release-header">Release Notes</div>', unsafe_allow_html=True)

# --- Information Section ---
st.markdown("---")

st.markdown("""
<div class="info-section">
    <div class="info-title">What are release notes?</div>
    <p>
        Versioning is a process of tracking changes to software over time, allowing users to understand 
        how the application has evolved and to easily reference improvements and new features. As changes 
        are made to the UI/UX of the application, they are documented here in the release notes with a 
        brief description of the change and the date it was made.
    </p>
    <p style="margin-top: 1rem;">
        We use version control systems to manage changes to the codebase, track changes over time, 
        roll back changes if necessary, and collaborate effectively on the application development.
    </p>
</div>
""", unsafe_allow_html=True)

# --- Versioning Info Section ---
st.markdown("---")
st.markdown("### 📋 Versioning Info")

col1, col2, col3= st.columns(3)

with col1:
    st.markdown("""
    <span style="color: #dc3545; font-weight: bold; font-size: 1.1rem;">Major Release</span>
    
    Significant new features, major architectural changes, or breaking changes that substantially 
    alter the application.
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <span style="color: #ff9800; font-weight: bold; font-size: 1.1rem;">Minor Release</span>
    
    New features, enhancements, or improvements that add functionality without breaking existing features.
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <span style="color: #6c757d; font-weight: bold; font-size: 1.1rem;">Patch Release</span>
    
    Bug fixes, small improvements, and maintenance updates that don't add new features.
    """, unsafe_allow_html=True)

# --- Helper Function to Render Release Entry ---
def render_release(date_str, version, title, badges, description, features=None):
    """
    Render a release entry with consistent formatting.
    
    Args:
        date_str: Date string (e.g., "Jan 15th 2025")
        version: Version number (e.g., "Version 1.0.0 beta")
        title: Release title
        badges: List of badge types ("major", "minor", "patch", "operational")
        description: Main description text
        features: Optional list of feature bullet points
    """
    # Badge HTML
    badge_html = ""
    badge_classes = {
        "major": "badge-major",
        "minor": "badge-minor",
        "patch": "badge-patch",
        "operational": "badge-operational"
    }
    badge_labels = {
        "major": "Major",
        "minor": "Minor",
        "patch": "Patch",
        "operational": "Operational pre-release"
    }
    
    for badge in badges:
        badge_class = badge_classes.get(badge.lower(), "badge-minor")
        badge_label = badge_labels.get(badge.lower(), badge)
        badge_html += f'<span class="badge {badge_class}">{badge_label}</span>'
    
    # Features HTML
    features_html = ""
    if features:
        features_html = "<ul style='margin-top: 1rem;'>"
        for feature in features:
            features_html += f"<li>{feature}</li>"
        features_html += "</ul>"
    
    # Complete entry HTML
    entry_html = f"""
    <div class="release-entry">
        <div class="release-date">{date_str}</div>
        <div class="release-version">{version}</div>
        <div class="release-title">{title}</div>
        <div>{badge_html}</div>
        <div class="release-description">
            {description}
            {features_html}
        </div>
    </div>
    """
    
    st.markdown(entry_html, unsafe_allow_html=True)


# --- Release Entries ---

# Example Release 1


# Example Release 2
render_release(
    date_str="November 23rd 2025",
    version="Version 5.1 beta",
    title="Authentication System Implementation",
    badges=["minor"],
    description="Added secure authentication for the Decision Engine tab while maintaining public access to analytical tools. Users can now log in to access advanced decision-making features.",
    features=[
        "Login system for Decision Engine tab",
        "Session-based authentication",
        "User logout functionality",
        "Public access maintained for Scatterplot and Choropleth tabs"
    ]
)


render_release(
    date_str="November 18th 2025",
    version="Version 5.0 beta",
    title="Added pages to the Decision Engine",
    badges=["major"],
    description="This version added pages to the Decision Engine, giving users more details and background information about the webapp.",
    features=[
        "Added pages to the Decision Engine",
        "Added About page",
        "Added Methodology page",
        "Added Resources page",
        "Added Versioning page",
    ]
)

render_release(
    date_str="November 14th 2025",
    version="Version 4.4 beta",
    title="Updated LDT-DE with lessons learned from Zambia",
    badges=["major"],
    description="This version updated the LDT-DE with lessons learned from Zambia, improving the accuracy and relevance of the analysis.",
    features=[
        "Updated indicators",
        "Added 3D Scatterplot",
        "Added Waterfall Score Driver Decomposition Charts",
        ""
    ]
)

render_release(
    date_str="November 12th 2025",
    version="Version 4.3 beta",
    title="Replaced Background Research content with SWOT Analysis",
    badges=["minor"],
    description="This version replaced the background research content with a SWOT analysis, improving the accuracy and relevance of the analysis.",
    features=[
        "SWOT analysis",
        "Users can now view a SWOT analysis of the region",
        "Users can now view the strengths, weaknesses, challenges, and opportunities of the region",
    ]
)

render_release(
    date_str="November 10th 2025",
    version="Version 4.2 beta",
    title="Added Chart and Plots from GPBP-LDT Webapp",
    badges=["major"],
    description="This version added chart and plots from the GPBP-LDT webapp to the Decision Engine, combining its functionalities with the GPBP LDT Webapp.",
    features=[
        "Chart and plots from the GPBP-LDT Webapp",
        "Users can now view charts and plots from the GPBP-LDT Webapp in the Decision Engine",
        "Users can now compare municipalities and regions across different indicators",
    ]
)

render_release(
    date_str="October 16th 2025",
    version="Version 4.1 beta",
    title="Added Web Search Tool",
    badges=["minor"],
    description="This version added a web search tool to the Decision Engine, allowing the LLM calls to search the web for information when needed.",
    features=[
        "Web search tool",
        "LLM calls can now search the web for information for the Background Research and Project Details sections"
    ]
)

render_release(
    date_str="October 16th 2025",
    version="Version 4.0 beta",
    title="Code Refactoring",
    badges=["major"],
    description="This version refactored the codebase to improve the readability and maintainability of the Decision Engine.",
    features=[
        "Refactored the codebase to improve the readability and maintainability of the Decision Engine",
        "Improved the codebase to be more modular and easier to understand"
    ]
)

render_release(
    date_str="October 16th 2025",
    version="Version 4.0 beta",
    title="Code Refactoring",
    badges=["major"],
    description="This version refactored the codebase to improve the readability and maintainability of the Decision Engine.",
    features=[
        "Refactored the codebase to improve the readability and maintainability of the Decision Engine",
        "Improved the codebase to be more modular and easier to understand"
    ]
)


render_release(
    date_str="September 20th 2025",
    version="Version 3.4 beta",
    title="LLM Response Format Standardization",
    badges=["minor"],
    description="This version standardized the response format for all LLM calls, improving the consistency and readability of the Decision Engine.",
    features=[
        "Standardized response format for all LLM calls",
        "All LLM responses are now formatted in a consistent manner",
        "Enforced specific formatting for all referenced Project"
    ]
)


render_release(
    date_str="August 15th 2025",
    version="Version 3.3 beta",
    title="Response Cache Dashboard",
    badges=["minor"],
    description="This version added a response cache dashboard to the Decision Engine, allowing users to view the cache and its contents.",
    features=[
        "Response cache dashboard",
        "Users can view the cache and check for number of responses, number of English and Serbian responses, cache version, and the last updated time",
        "Users can clear the cache",
    ]
)

render_release(
    date_str="August 10th 2025",
    version="Version 3.2 beta",
    title="Response Caching",
    badges=["minor"],
    description="This version added response caching for all LLM calls, improving the reliability and cost-effectiveness of the Decision Engine.",
    features=[
        "Response caching for all LLM calls",
        "Decision Engine will always check the cache for a response before making a new call to the LLM",
        "If a response is found in the cache, it will be returned immediately",
        "If a response is not found in the cache, a new call to the LLM will be made and the response will be cached for future use"
    ]
)

render_release(
    date_str="Jun 29th 2025",
    version="Version 3.1 beta",
    title="Prompt Refinement, Bug Fixes",
    badges=["minor", "patch"],
    description="This release refines the prompts used for the regional analysis and project recommendation engine, improving the accuracy and relevance of the analysis.",
    features=[
        "Refined prompts for the project recommendation section",
        "Adjusted prompting temperature for all LLM calls "
        "Fixed minor functional bugs"
    ]
)


render_release(
    date_str="Jun 13th 2025",
    version="Version 3.0 beta",
    title="Centralized workflows",
    badges=["major"],
    description="This release centralizes the DE's workflow. Now, both the English and Serbian workflows use the same prompts in English, with the Serbian workflow being pure translation of the English workflow.",
    features=[
        "Centralized workflows for the Decision Engine",
        "Designated the English workflow as the default workflow",
        "Created a separate, one-shot translation agent from English to Serbian"
    ]
)


render_release(
    date_str="Jun 11th 2025",
    version="Version 2.2 beta",
    title="Prompts Refinement",
    badges=["minor"],
    description="This release refines the prompts used for the regional analysis and project recommendation engine, improving the accuracy and relevance of the analysis.",
    features=[
        "Refined prompts for the project recommendation engine",
    ]
)

render_release(
    date_str="Apr 21st 2025",
    version="Version 2.1 beta",
    title="Prompts Refinement",
    badges=["minor", "patch"],
    description="This release refines the prompts used for the regional analysis and project recommendation engine, improving the accuracy and relevance of the analysis.",
    features=[
        "Refined prompts for the regional analysis and project recommendation engine",
        "Improved accuracy and relevance of the analysis",
        "Overall logic remains the same"
        "Fixed minor functional bugs"
    ]
)


render_release(
    date_str="Apr 15th 2025",
    version="Version 2.0 beta",
    title="Added Support for Multiple Languages",
    badges=["major"],
    description="This release adds support for multiple languages, allowing users to choose between English and Serbian Cyrillic.",
    features=[
        "Multi-language support (English and Serbian Cyrillic)",
        "The English and Serbian workflows are now separated, each using prompts in the respective language."
        "Overall logic remains the same"
    ]
)

render_release(
    date_str="Apr 1st 2025",
    version="Version 1.0 beta",
    title="Initial Decision Engine Release",
    badges=["major"],
    description="First operational release of the Local Development Tracker Decision Engine. This release introduces AI-powered analysis for regional development planning, integrated with comprehensive indicator data and project recommendations.",
    features=[
        "AI-powered selection of relevant indicators for the regional analysis",
        "Regional indicator analysis with historical trends (text-based)",
        "Project recommendation engine",
    ]
)


# Add more releases here as needed...

# --- Footer ---
st.markdown("---")
st.markdown(f"*Last updated: {datetime.now().strftime('%B %d, %Y')}*")
