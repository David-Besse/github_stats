#!/usr/bin/python3

import asyncio
import os
import re
import aiohttp
from github_stats import Stats

################################################################################
# Helper Functions
################################################################################

def generate_output_folder() -> None:
    """
    Create the output folder if it does not already exist
    """
    if not os.path.isdir("generated"):
        os.mkdir("generated")
        os.chmod("generated", 0o777)  # Ajuster les permissions si nécessaire
        print("Created directory: generated with permissions 777")
    else:
        print("Directory already exists: generated")

def check_permissions() -> None:
    """
    Check necessary permissions for templates and generated folder
    """
    # Vérifier si le répertoire "templates" existe
    if not os.path.isdir("templates"):
        raise FileNotFoundError("The 'templates' directory does not exist")

    # Vérifier si les fichiers de modèle existent
    if not os.path.isfile("templates/overview.svg"):
        raise FileNotFoundError("The file 'templates/overview.svg' does not exist")
    if not os.path.isfile("templates/languages.svg"):
        raise FileNotFoundError("The file 'templates/languages.svg' does not exist")

    # Vérifier les permissions de lecture sur les fichiers de modèle
    if not os.access("templates/overview.svg", os.R_OK):
        raise PermissionError("Cannot read 'templates/overview.svg'")
    if not os.access("templates/languages.svg", os.R_OK):
        raise PermissionError("Cannot read 'templates/languages.svg'")

    # Vérifier les permissions d'écriture sur le répertoire "generated"
    if not os.access("generated", os.W_OK):
        raise PermissionError("Cannot write to 'generated' directory")

################################################################################
# Individual Image Generation Functions
################################################################################

async def generate_overview(s: Stats) -> None:
    """
    Generate an SVG badge with summary statistics
    :param s: Represents user's GitHub statistics
    """
    with open("templates/overview.svg", "r") as f:
        output = f.read()

    output = re.sub("{{ name }}", await s.name, output)
    output = re.sub("{{ stars }}", f"{await s.stargazers:,}", output)
    output = re.sub("{{ forks }}", f"{await s.forks:,}", output)
    output = re.sub("{{ contributions }}", f"{await s.total_contributions:,}", output)
    changed = (await s.lines_changed)[0] + (await s.lines_changed)[1]
    output = re.sub("{{ lines_changed }}", f"{changed:,}", output)
    output = re.sub("{{ views }}", f"{await s.views:,}", output)
    output = re.sub("{{ repos }}", f"{len(await s.repos):,}", output)

    generate_output_folder()
    with open("generated/overview.svg", "w") as f:
        f.write(output)
        print("Generated file: generated/overview.svg")

async def generate_languages(s: Stats) -> None:
    """
    Generate an SVG badge with summary languages used
    :param s: Represents user's GitHub statistics
    """
    with open("templates/languages.svg", "r") as f:
        output = f.read()

    progress = ""
    lang_list = ""
    sorted_languages = sorted(
        (await s.languages).items(), reverse=True, key=lambda t: t[1].get("size")
    )
    delay_between = 150
    for i, (lang, data) in enumerate(sorted_languages):
        color = data.get("color")
        color = color if color is not None else "#000000"
        progress += (
            f'<span style="background-color: {color};'
            f'width: {data.get("prop", 0):0.3f}%;" '
            f'class="progress-item"></span>'
        )
        lang_list += f"""
<li style="animation-delay: {i * delay_between}ms;">
<svg xmlns="http://www.w3.org/2000/svg" class="octicon" style="fill:{color};"
viewBox="0 0 16 16" version="1.1" width="16" height="16"><path
fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8z"></path></svg>
<span class="lang">{lang}</span>
<span class="percent">{data.get("prop", 0):0.2f}%</span>
</li>

"""

    output = re.sub(r"{{ progress }}", progress, output)
    output = re.sub(r"{{ lang_list }}", lang_list, output)

    generate_output_folder()
    with open("generated/languages.svg", "w") as f:
        f.write(output)
        print("Generated file: generated/languages.svg")

################################################################################
# Main Function
################################################################################

async def main() -> None:
    """
    Generate all badges
    """
    generate_output_folder()  # Assurez-vous que le dossier est créé avec les bonnes permissions
    check_permissions()

    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        raise Exception("A personal access token is required to proceed!")
    user = os.getenv("GITHUB_ACTOR")
    if user is None:
        raise RuntimeError("Environment variable GITHUB_ACTOR must be set.")
    exclude_repos = os.getenv("EXCLUDED")
    excluded_repos = (
        {x.strip() for x in exclude_repos.split(",")} if exclude_repos else None
    )
    exclude_langs = os.getenv("EXCLUDED_LANGS")
    excluded_langs = (
        {x.strip() for x in exclude_langs.split(",")} if exclude_langs else None
    )
    raw_ignore_forked_repos = os.getenv("EXCLUDE_FORKED_REPOS")
    ignore_forked_repos = (
        not not raw_ignore_forked_repos
        and raw_ignore_forked_repos.strip().lower() != "false"
    )
    async with aiohttp.ClientSession() as session:
        s = Stats(
            user,
            access_token,
            session,
            exclude_repos=excluded_repos,
            exclude_langs=excluded_langs,
            ignore_forked_repos=ignore_forked_repos,
        )
        await asyncio.gather(generate_languages(s), generate_overview(s))

if __name__ == "__main__":
    asyncio.run(main())
