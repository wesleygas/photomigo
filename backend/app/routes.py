from fastapi import Depends, HTTPException, APIRouter, Header
from typing import Annotated

from fastapi.responses import Response
from io import BytesIO
from PIL import Image, ImageEnhance
import requests
import qrcode
from collections.abc import Generator
from sqlmodel import Session, select

from app.models import Device, Group
from app.config import settings
from app.db import engine


router = APIRouter(prefix="")

def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_db)]

def get_group_by_machine(session: Session, machine: str) -> Group:
    statement = select(Group).where(Device.id == machine, Group.id == Device.group_id)
    return session.exec(statement).one()

def fetch_image_from_immich(image_url):
    response = requests.get(image_url, stream=True, headers={"x-api-key": settings.IMMICH_API_KEY})
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Image not found at the provided URL")
    image = Image.open(response.raw).convert("RGB")
    image.thumbnail((320, 240))
    image = image.rotate(180)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.2)  # Increase contrast by 20%
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(0.8)  # Increase brightness by 10%
    byte_io = BytesIO()
    image.save(byte_io, format="BMP")
    byte_io.seek(0)
    return byte_io


def build_qr_url(url):
    # Generate a QR code for the given URL
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    # Create the image of the QR code
    qr_image = qr.make_image(fill="black", back_color="white").convert("RGB")
    qr_image = qr_image.resize((240, 240))
    # Convert the QR code image to BMP format
    byte_io = BytesIO()
    qr_image.save(byte_io, format="BMP")
    byte_io.seek(0)
    return byte_io


@router.get("/image")
async def get_image(
        session: SessionDep, 
        machine: Annotated[str, Header()],
        advance: bool = False
    ):
    try:
        # Fetch the image from the provided URL
        # print(machine)
        grp = get_group_by_machine(session, machine)
        response = requests.get(f"{settings.IMMICH_API_PATH}/albums/{grp.album_id}", stream=True, headers={"x-api-key": settings.IMMICH_API_KEY})
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Error finding image ID")
        album_assets = response.json()['assets']
        grp.current_asset = (grp.current_asset + 1)%len(album_assets) if advance else grp.current_asset
        image_id = album_assets[grp.current_asset]['id']
        image_url = f'{settings.IMMICH_API_PATH}/assets/{image_id}/thumbnail?size=preview'
        session.add(grp)
        session.commit()
        return Response(content=fetch_image_from_immich(image_url).getvalue(), media_type="image/bmp")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.get("/qrcode")
async def get_qrcode(
        session: SessionDep, 
        machine: Annotated[str, Header()]
    ):
    try:
        # print(machine)
        grp = get_group_by_machine(session, machine)
        # print(grp)
        return Response(content=build_qr_url(grp.album_url).getvalue(), media_type="image/bmp")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    

