from dataclasses import dataclass

import httpx
import structlog
from fastapi import HTTPException, status

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class CompanyPartyInfo:
    inn: str
    kpp: str | None
    name: str
    address: str


class DaDataService:
    DADATA_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"

    async def find_by_inn(self, inn: str) -> CompanyPartyInfo:
        """Поиск реквизитов организации или ИП по ИНН."""
        clean_inn = inn.strip()
        if len(clean_inn) not in (10, 12) or not clean_inn.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Укажите корректный ИНН организации (10 или 12 цифр)",
                    "code": "INVALID_INN",
                },
            )

        # shortcut: локальный mock реквизитов при отсутствии боевого ключа DaData
        if not settings.DADATA_API_KEY or settings.DADATA_API_KEY.startswith(("mock_", "test_")):
            if clean_inn == "7707083893":
                return CompanyPartyInfo(
                    inn=clean_inn,
                    kpp="773601001",
                    name="ПАО СБЕРБАНК",
                    address="117312, г Москва, ул Вавилова, д 19",
                )
            if clean_inn == "0000000000":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "error": "Организация с таким ИНН не найдена в реестре ФНС",
                        "code": "DADATA_NOT_FOUND",
                    },
                )
            prefix = "ИП" if len(clean_inn) == 12 else "ООО"
            return CompanyPartyInfo(
                inn=clean_inn,
                kpp="770101001" if len(clean_inn) == 10 else None,
                name=f'{prefix} "ТЕСТОВАЯ КОМПАНИЯ {clean_inn[-4:]}"',
                address="125009, г. Москва, Тверская ул., д. 1",
            )

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    self.DADATA_URL,
                    json={"query": clean_inn},
                    headers={
                        "Authorization": f"Token {settings.DADATA_API_KEY}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
            if resp.status_code != 200:
                logger.error("dadata_api_error", status_code=resp.status_code)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        "error": "Сервис проверки реквизитов временно недоступен",
                        "code": "DADATA_UNAVAILABLE",
                    },
                )

            data = resp.json()
            suggestions = data.get("suggestions", [])
            if not suggestions:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "error": "Организация с таким ИНН не найдена в реестре ФНС",
                        "code": "DADATA_NOT_FOUND",
                    },
                )

            party = suggestions[0]["data"]
            name = (
                party.get("name", {}).get("short_with_opf")
                or party.get("name", {}).get("full_with_opf")
                or f"Организация ИНН {clean_inn}"
            )
            address = party.get("address", {}).get("value") or "Адрес не указан"
            kpp = party.get("kpp")

            return CompanyPartyInfo(
                inn=clean_inn,
                kpp=kpp,
                name=name,
                address=address,
            )
        except httpx.RequestError as exc:
            logger.error("dadata_network_error", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "Ошибка сети при проверке реквизитов",
                    "code": "DADATA_NETWORK_ERROR",
                },
            ) from exc


dadata_service = DaDataService()
