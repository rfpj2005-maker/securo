from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.services.drivvo_import_service import parse_decimal, split_tables

# Same shape as a real Drivvo web export: Latin-1, one CSV with `#Section`
# tables, `.` decimals, a trailing comma on the vehicle rows, and an
# unquoted inspection table where a comma in free text adds a column.
DRIVVO_CSV = """
#Veículo

"Nome do veículo","Ativo","Tipo de veículo","Marca","Modelo","Placa","Ano","Vol. do tanque(gal)","Odômetro (km)","Chassi","Renavam","Observação",
"Gol ABC1D23","Sim","Carro","VW","Gol","ABC1D23","2019","50.000","Quilômetros (km)","","","",
"Kombi XYZ9A87","Não","Carro","VW","Kombi","XYZ9A87","","","Quilômetros (km)","","","",

#Abastecimento

"Nome do veículo","Odômetro (km)","Data","Combustível",  "Preço / gal",  "Valor total",  "Volume","Completou o tanque","Segundo combustível","Preço / gal","Valor total","Volume","Completou o tanque 2","Terceiro combustível","Preço / gal","Valor total","Volume","Completou o tanque 3","Média","Média 2","Média 3","Tipo de recarga","Bateria inicial (%)","Bateria final (%)","Duração (min)","Posto de combustível","Motorista","Forma de pagamento","Motivo","Observação","(System Date)"
"Gol ABC1D23","10500","10/09/2026 08:00","Gas. Comum","6.00","180","30.000","Sim","","0","0","0","Não","","0","0","0","Não","12.5","","","","0","0","0","Posto Centro","Motorista A","pix","Trabalho","","10/09/2026 11:00"
"Gol ABC1D23","10200","05/09/2026 08:00","Gas. Comum","6.00","60","10.000","Não","","0","0","0","Não","","0","0","0","Não","","","","","0","0","0","Posto Centro","Motorista A","","","","05/09/2026 11:00"
"Gol ABC1D23","10000","01/09/2026 08:00","Gas. Comum","6.25","250","40.000","Sim","","0","0","0","Não","","0","0","0","Não","","","","","0","0","0","Posto Centro","Motorista B","","","","01/09/2026 11:00"

#Serviço

"Nome do veículo","Odômetro (km)","Data","Valor total","Tipo de serviço","Local do serviço","Motorista","Forma de pagamento","Observação","(System Date)"
"Gol ABC1D23","10450","08/09/2026 19:58","144","Troca de Óleo","Oficina X","Motorista A","Dinheiro","pago no pix","08/09/2026 23:00"

#Percurso

"Nome do veículo","Data inicial","Data final","Odômetro inicial","Odômetro final","Distância (km)","Valor km","Total","Origem","Destino","Tipo de carga","Contratante","Quantidade","Unidade medida","Peso","Volume (m³)","Valor do frete","Motorista","Motivo","Observação","(System Date)"
"Gol ABC1D23","11/09/2026 06:52","11/09/2026 18:00","10500","10620","120","0","0","Casa","Matriz","","","0","","0","0","0","Motorista A","Trabalho","visitas","11/09/2026 19:00"
"Kombi XYZ9A87","11/09/2026 07:00","11/09/2026 08:00","50000","49990","-10","0","0","A","B","","","0","","0","0","0","Motorista B","","","11/09/2026 19:00"

#Inspeção Diária do veículo

"Nome do veículo","Odômetro (km)","Data","Motorista",Documento do veículo está disponível?,Pneus estão em bom estado?,Foi verificado o nível do liquido do radiador?,Quais destes itens NÃO estão funcionando?,Outro problema (descreva),"Observação","(System Date)"
Gol ABC1D23,10620,12/09/2026 06:54,Motorista A,Sim,Sim,Sim,,,,12/09/2026 09:56
Gol ABC1D23,0,12/09/2026 21:00,Motorista B,Sim,Sim,Sim,,,,12/09/2026 21:05
Gol ABC1D23,10700,13/09/2026 06:11,Motorista A,Não,Sim,Sim,Setas,Ao soltar o pedal, faz barulho,,13/09/2026 11:14
""".encode("latin-1")


def _upload(content: bytes = DRIVVO_CSV) -> dict:
    return {"file": ("20261009_REPORTS_DRIVVO.csv", content, "text/csv")}


def test_parse_decimal_handles_both_separators():
    assert parse_decimal("12.841") == Decimal("12.841")
    assert parse_decimal("1.234,56") == Decimal("1234.56")
    assert parse_decimal("6,23") == Decimal("6.23")
    assert parse_decimal("") is None


def test_split_tables_finds_every_section():
    tables = split_tables(DRIVVO_CSV.decode("latin-1"))
    assert set(tables) == {"veiculo", "abastecimento", "servico", "percurso", "inspecao diaria do veiculo"}
    assert len(tables["abastecimento"].rows) == 3


@pytest.mark.asyncio
async def test_dry_run_previews_without_saving(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.post(
        "/api/vehicles/import/drivvo", params={"dry_run": True}, files=_upload(), headers=auth_headers
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["dry_run"] is True
    assert sorted(data["vehicles_created"]) == ["Gol ABC1D23", "Kombi XYZ9A87"]
    assert data["records"] == {"created": 4, "skipped": 0}
    assert data["trips"] == {"created": 1, "skipped": 0}
    assert data["inspections"] == {"created": 3, "skipped": 0}
    # The Kombi trip runs the odometer backwards and is reported, not imported.
    assert any("Percurso linha 2" in w for w in data["warnings"])

    assert (await client.get("/api/vehicles", headers=auth_headers)).json() == []


@pytest.mark.asyncio
async def test_import_creates_everything_and_is_idempotent(
    client: AsyncClient, auth_headers: dict, test_user: User
):
    response = await client.post("/api/vehicles/import/drivvo", files=_upload(), headers=auth_headers)
    assert response.status_code == 200, response.text

    vehicles = {v["name"]: v for v in (await client.get("/api/vehicles", headers=auth_headers)).json()}
    gol = vehicles["Gol ABC1D23"]
    assert gol["plate"] == "ABC1D23"
    assert gol["year"] == 2019
    assert float(gol["tank_capacity"]) == 50.0
    assert vehicles["Kombi XYZ9A87"]["is_active"] is False

    stats = gol["stats"]
    # Lowest reading in the file becomes the starting odometer (a blank "0"
    # reading doesn't count); the latest inspection is the highest reading.
    assert gol["initial_odometer"] == 10000
    assert stats["current_odometer"] == 10700
    assert stats["fuel_cost"] == "490.00"
    assert stats["maintenance_cost"] == "144.00"
    assert stats["avg_consumption"] == "12.50"
    assert stats["trip_count"] == 1
    assert stats["last_inspection_has_issue"] is True

    records = (await client.get(f"/api/vehicles/{gol['id']}/records", headers=auth_headers)).json()
    fill = next(r for r in records if r["odometer"] == 10500)
    assert fill["place"] == "Posto Centro"
    assert fill["driver"] == "Motorista A"
    assert fill["payment_method"] == "pix"
    assert fill["purpose"] == "Trabalho"
    partial = next(r for r in records if r["odometer"] == 10200)
    assert partial["full_tank"] is False
    service = next(r for r in records if r["kind"] == "maintenance")
    assert service["description"] == "Troca de Óleo"
    assert service["place"] == "Oficina X"

    trips = (await client.get(f"/api/vehicles/{gol['id']}/trips", headers=auth_headers)).json()
    assert trips[0]["distance"] == 120
    assert trips[0]["origin"] == "Casa"
    assert trips[0]["destination"] == "Matriz"

    inspections = (await client.get(f"/api/vehicles/{gol['id']}/inspections", headers=auth_headers)).json()
    latest = inspections[0]
    assert latest["documents_ok"] is False
    assert latest["failing_items"] == "Setas"
    # The unquoted comma is glued back into the free-text answer.
    assert latest["other_problem"] == "Ao soltar o pedal, faz barulho"
    assert latest["has_issue"] is True
    assert inspections[1]["odometer"] is None
    assert inspections[2]["has_issue"] is False

    again = (await client.post("/api/vehicles/import/drivvo", files=_upload(), headers=auth_headers)).json()
    assert again["vehicles_created"] == []
    assert sorted(again["vehicles_matched"]) == ["Gol ABC1D23", "Kombi XYZ9A87"]
    assert again["records"] == {"created": 0, "skipped": 4}
    assert again["trips"] == {"created": 0, "skipped": 1}
    assert again["inspections"] == {"created": 0, "skipped": 3}


@pytest.mark.asyncio
async def test_import_matches_existing_vehicle_by_plate(client: AsyncClient, auth_headers: dict, test_user: User):
    existing = await client.post(
        "/api/vehicles", json={"name": "Carro da empresa", "plate": "abc-1d23"}, headers=auth_headers
    )
    data = (await client.post("/api/vehicles/import/drivvo", files=_upload(), headers=auth_headers)).json()
    assert data["vehicles_matched"] == ["Carro da empresa"]
    assert data["vehicles_created"] == ["Kombi XYZ9A87"]
    records = (
        await client.get(f"/api/vehicles/{existing.json()['id']}/records", headers=auth_headers)
    ).json()
    assert len(records) == 4


@pytest.mark.asyncio
async def test_import_rejects_non_drivvo_file(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.post(
        "/api/vehicles/import/drivvo", files=_upload(b"date,amount\n2026-01-01,10\n"), headers=auth_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_trip_and_inspection_crud(client: AsyncClient, auth_headers: dict, test_user: User):
    vehicle = (await client.post("/api/vehicles", json={"name": "Van"}, headers=auth_headers)).json()
    vid = vehicle["id"]

    bad = await client.post(
        f"/api/vehicles/{vid}/trips",
        json={"started_at": "2026-10-01T08:00:00", "start_odometer": 500, "end_odometer": 400},
        headers=auth_headers,
    )
    assert bad.status_code == 422

    trip = await client.post(
        f"/api/vehicles/{vid}/trips",
        json={"started_at": "2026-10-01T08:00:00", "start_odometer": 400, "end_odometer": 480, "driver": "X"},
        headers=auth_headers,
    )
    assert trip.status_code == 201
    assert trip.json()["distance"] == 80
    tid = trip.json()["id"]

    response = await client.patch(
        f"/api/vehicles/{vid}/trips/{tid}", json={"end_odometer": 300}, headers=auth_headers
    )
    assert response.status_code == 400

    inspection = await client.post(
        f"/api/vehicles/{vid}/inspections",
        json={"inspected_at": "2026-10-02T07:00:00", "odometer": 490, "tires_ok": False},
        headers=auth_headers,
    )
    assert inspection.status_code == 201
    assert inspection.json()["has_issue"] is True
    iid = inspection.json()["id"]

    stats = (await client.get(f"/api/vehicles/{vid}", headers=auth_headers)).json()["stats"]
    assert stats["current_odometer"] == 490
    assert stats["trip_count"] == 1

    patched = await client.patch(
        f"/api/vehicles/{vid}/inspections/{iid}", json={"tires_ok": True}, headers=auth_headers
    )
    assert patched.json()["has_issue"] is False

    assert (await client.delete(f"/api/vehicles/{vid}/trips/{tid}", headers=auth_headers)).status_code == 204
    assert (await client.delete(f"/api/vehicles/{vid}/inspections/{iid}", headers=auth_headers)).status_code == 204
    assert (await client.get(f"/api/vehicles/{vid}/trips", headers=auth_headers)).json() == []
