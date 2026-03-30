"""Backup router - export and import user data."""

import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.collection import Collection, CollectionRepo
from models.repo_note import RepoNote
from models.user import User
from routers.deps import get_current_user


router = APIRouter(prefix="/api", tags=["backup"])


@router.get("/backup/export")
async def export_data(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Export all user data as JSON."""
    # Export collections with repos (user's own collections only)
    collections_result = await db.execute(
        select(Collection).where(Collection.user_id == current_user.id)
    )
    collections = collections_result.scalars().all()

    collections_data = []
    for col in collections:
        # Get repos in this collection
        repos_result = await db.execute(
            select(CollectionRepo).where(CollectionRepo.collection_id == col.id)
        )
        repos_links = repos_result.scalars().all()

        repos_data = [
            {"repo_id": link.repo_id, "notes": link.notes}
            for link in repos_links
        ]

        collections_data.append({
            "name": col.name,
            "description": col.description,
            "tags": col.tags,
            "color": col.color,
            "icon": col.icon,
            "repos": repos_data,
        })

    # Export repo notes (user's own notes only)
    notes_result = await db.execute(
        select(RepoNote).where(RepoNote.user_id == current_user.id)
    )
    notes = notes_result.scalars().all()

    notes_data = [
        {"repo_id": note.repo_id, "note": note.note}
        for note in notes
    ]

    export_data = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "collections": collections_data,
        "repo_notes": notes_data,
    }

    filename = f"starmind-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/backup/import")
async def import_data(
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """Import user data from JSON backup file."""
    if not file.filename or not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Please upload a JSON file")

    try:
        content = await file.read()
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    # Validate version
    if data.get("version") != "1.0":
        raise HTTPException(status_code=400, detail="Unsupported backup version")

    stats = {"collections": 0, "notes": 0, "repos_added": 0}

    # Import collections (associate with current user)
    for col_data in data.get("collections", []):
        # Create collection for current user
        collection = Collection(
            user_id=current_user.id,
            name=col_data["name"],
            description=col_data.get("description", ""),
            tags=col_data.get("tags", "[]"),
            color=col_data.get("color", "#3B82F6"),
            icon=col_data.get("icon", "folder"),
        )
        db.add(collection)
        await db.flush()  # Get the ID

        # Add repos to collection
        for repo_link in col_data.get("repos", []):
            link = CollectionRepo(
                collection_id=collection.id,
                repo_id=repo_link["repo_id"],
                notes=repo_link.get("notes", ""),
            )
            db.add(link)
            stats["repos_added"] += 1

        stats["collections"] += 1

    # Import repo notes (associate with current user)
    for note_data in data.get("repo_notes", []):
        note = RepoNote(
            repo_id=note_data["repo_id"],
            user_id=current_user.id,
            note=note_data["note"],
        )
        db.add(note)
        stats["notes"] += 1

    await db.commit()

    return {
        "message": "Import successful",
        "stats": stats
    }
