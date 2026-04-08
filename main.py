import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.api import router
from app.graphql_api import graphql_router

app = FastAPI(
    title="Slay the Spire 2 Deck Builder API",
    description="Deck Builder Tool for Slay the Spire 2, providing card data, character info, and deck management features. Based on ptrlrd/spire-codex.",
    version="1.0.0",
)

# include all real API routes
app.include_router(router)
app.include_router(graphql_router, prefix="/graphql", include_in_schema=False)

@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)