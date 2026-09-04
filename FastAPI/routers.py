from datetime import datetime,date

from fastapi import (
    APIRouter,
    Query,
    HTTPException
)

from database import engine

from models import (
    NetworkSummaryResponse,
    GridActivityResponse,
    HotspotResponse,
    AlertResponse,
    GridFeaturesResponse,
    RiskPredictionRequest,
    RiskPredictionResponse,
    PipelineStatusResponse,
    GridLocationResponse,
    TopMoversResponse
)

from services import (
    NetworkService
)

router = APIRouter()

service = NetworkService(engine)


@router.get(
    "/network/summary",
    response_model=NetworkSummaryResponse
)
def network_summary(
    as_of: datetime | None = None
):

    return service.get_network_summary(
        as_of
    )


@router.get(
    "/network/grid/{grid_id}",
    response_model=
    GridActivityResponse
)
def get_grid_activity(

    grid_id: int,

    date: date | None = None,

    hour: int | None = None,

    as_of: datetime | None = None

):

    try:

        return service.get_grid_activity(
            grid_id=grid_id,
            date=date,
            hour=hour,
            as_of=as_of
        )

    except HTTPException:

        raise

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=
            f"Unable to retrieve grid activity: {str(ex)}"
        )

@router.get(
    "/network/hotspots",
    response_model=HotspotResponse
)
def hotspots(

    limit: int = 10,

    as_of: datetime | None = None

):

    try:

        return service.get_hotspots(
            limit=limit,
            as_of=as_of
        )

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )

@router.get(
    "/network/alerts",
    response_model=AlertResponse
)
def alerts(

    limit: int = 10,

    severity: str | None = None,

    as_of: datetime | None = None

):

    try:

        return service.get_alerts(
            severity=severity,
            limit=limit,
            as_of=as_of
        )

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )


@router.get(
    "/network/grid/{grid_id}/features",
    response_model=
    GridFeaturesResponse
)
def get_grid_features(
    grid_id: int
):

    try:

        return service.get_grid_features(
            grid_id
        )

    except HTTPException:

        raise

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=
            f"Unable to retrieve features: "
            f"{str(ex)}"
        )

@router.post(
    "/network/predict-risk",
    response_model=
    RiskPredictionResponse
)
def predict_risk(
    request: RiskPredictionRequest
):

    try:

        return service.predict_risk(
            request
        )

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=
            f"Unable to generate prediction: "
            f"{str(ex)}"
        )


@router.get(
    "/pipeline/status",
    response_model=
    PipelineStatusResponse
)
def pipeline_status():

    try:

        return service.get_pipeline_status()

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=
            f"Unable to read pipeline status: "
            f"{str(ex)}"
        )


@router.get(
    "/network/grid/{grid_id}/location",
    response_model=
    GridLocationResponse
)
def get_grid_location(
    grid_id: int
):

    try:

        return service.get_grid_location(
            grid_id
        )

    except HTTPException:

        raise

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=
            f"Unable to retrieve grid location: "
            f"{str(ex)}"
        )


@router.get(
    "/network/top-movers",
    response_model=
    TopMoversResponse
)
def top_movers(

    limit: int = Query(10, ge=1, le=50),

    as_of: datetime | None = None

):

    try:

        return service.get_top_movers(
            limit=limit,
            as_of=as_of
        )

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=
            f"Unable to retrieve top movers: "
            f"{str(ex)}"
        )