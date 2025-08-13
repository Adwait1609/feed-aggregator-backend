from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_clusters():
    """Get article clusters - placeholder for now"""
    return {"message": "Clustering feature coming soon!"}
