from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field


class HealthUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: Literal["UPA", "UBS"]
    address: str
    latitude: float
    longitude: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def position(self) -> tuple[float, float]:
        """[latitude, longitude], formato usado pelo Leaflet no frontend."""
        return (self.latitude, self.longitude)
