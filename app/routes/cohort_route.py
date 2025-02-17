import json

from fastapi import APIRouter
import app.services.fhir_client as fhir_client

router = APIRouter()
client = fhir_client.FHIRClient()

@router.post("/cohort/select")
async def run_select(cohort_definition: object):
    print(json.dumps(cohort_definition))
