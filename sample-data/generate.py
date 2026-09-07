# -*- coding: utf-8 -*-
"""Generates a small, internally-consistent, synthetic Romanian sample-data
set for FoldarAI pipeline testing (invoices, contracts, HR docs, emails,
accounting spreadsheet) for one fictional company, "Atelierul Verde SRL".

Usage: python3 generate.py   (needs openpyxl - pip install openpyxl)
Regenerates dump/, manifest.json in this same directory. Idempotent for
existing filenames; if you rename/remove entries in DUMP_NAMES etc., delete
dump/ and manifest.json first so stale files don't linger.
"""
import os
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

ROOT = str(Path(__file__).resolve().parent)

COMPANY = {
    "name": "Atelierul Verde SRL",
    "cui": "RO12345678",
    "j": "J12/456/2018",
    "address": "Str. Fabricii nr. 10, Cluj-Napoca, jud. Cluj",
    "iban": "RO49AAAA1B31007593840000",
    "bank": "Banca Transilvania",
}

PARTNERS = {
    "lemn-prod": {"name": "Lemn Prod SRL", "cui": "RO23456789", "j": "J06/112/2015",
                  "address": "Str. Padurii nr. 5, Bistrita, jud. Bistrita-Nasaud", "type": "furnizor"},
    "feronerie-est": {"name": "Feronerie Est SRL", "cui": "RO34567890", "j": "J22/331/2016",
                       "address": "Str. Industriilor nr. 22, Iasi, jud. Iasi", "type": "furnizor"},
    "vopsele-rapid": {"name": "Vopsele Rapid SRL", "cui": "RO45678901", "j": "J40/998/2019",
                       "address": "Str. Chimistilor nr. 3, Bucuresti, sector 3", "type": "furnizor"},
    "transport-nord": {"name": "Transport Nord SRL", "cui": "RO56789012", "j": "J06/77/2014",
                        "address": "Str. Transportatorilor nr. 8, Bistrita, jud. Bistrita-Nasaud", "type": "furnizor"},
    "mobilier-deco": {"name": "Mobilier Deco SRL", "cui": "RO67890123", "j": "J12/890/2017",
                       "address": "Str. Decoratorilor nr. 14, Cluj-Napoca, jud. Cluj", "type": "client"},
    "cabinet-ionescu": {"name": "Cabinet de Avocatura Ionescu", "cui": "RO78901234", "j": "-",
                         "address": "Str. Justitiei nr. 2, Cluj-Napoca, jud. Cluj", "type": "client"},
    "popescu-andrei": {"name": "Popescu Andrei (persoana fizica)", "cui": "CNP 1850101123456", "j": "-",
                        "address": "Str. Primaverii nr. 44, Cluj-Napoca, jud. Cluj", "type": "client"},
}

# (id, partner_key, date, [(descriere, cant, um, pret_unitar_fara_tva), ...])
INVOICES = [
    ("FLP-014", "lemn-prod", "2025-01-15", [
        ("Panou lemn masiv stejar 18mm", 12, "buc", 210.00),
        ("Cherestea rasinoase 50x100", 40, "ml", 38.50),
        ("Transport marfa la depozit", 1, "serv", 480.42),
    ]),
    ("FLP-031", "lemn-prod", "2025-03-10", [
        ("Panou lemn masiv fag 18mm", 15, "buc", 235.00),
        ("Furnir stejar natural", 25, "mp", 96.60),
    ]),
    ("FLP-052", "lemn-prod", "2025-05-20", [
        ("Panou lemn masiv stejar 25mm", 10, "buc", 310.00),
        ("Lambriu brad natural", 60, "ml", 24.20),
    ]),
    ("FLP-061", "lemn-prod", "2025-06-05", [
        ("Panou lemn masiv stejar 18mm", 22, "buc", 210.00),
        ("Panou lemn masiv stejar 25mm", 8, "buc", 310.00),
        ("Furnir stejar natural", 20, "mp", 96.60),
        ("Transport marfa - comanda urgenta", 1, "serv", 606.66),
    ]),
    ("FLP-078", "lemn-prod", "2025-08-12", [
        ("Cherestea rasinoase 50x100", 50, "ml", 38.50),
        ("Panou lemn masiv fag 18mm", 8, "buc", 235.00),
    ]),
    ("FLP-096", "lemn-prod", "2025-10-07", [
        ("Panou lemn masiv stejar 18mm", 14, "buc", 210.00),
        ("Furnir stejar natural", 18, "mp", 96.60),
        ("Transport marfa la depozit", 1, "serv", 291.60),
    ]),
    ("FFE-022", "feronerie-est", "2025-02-18", [
        ("Balamale mobilier inchidere lenta", 80, "buc", 8.90),
        ("Glisiere sertar 45cm", 30, "set", 17.50),
    ]),
    ("FFE-039", "feronerie-est", "2025-04-22", [
        ("Manere inox mobilier", 60, "buc", 9.80),
        ("Suruburi mobilier set 200 buc", 4, "set", 45.50),
    ]),
    ("FFE-058", "feronerie-est", "2025-06-15", [
        ("Balamale mobilier inchidere lenta", 120, "buc", 8.90),
        ("Glisiere sertar 45cm", 50, "set", 17.50),
        ("Manere inox mobilier", 40, "buc", 9.80),
    ]),
    ("FFE-081", "feronerie-est", "2025-09-09", [
        ("Glisiere sertar 60cm", 40, "set", 19.90),
        ("Suruburi mobilier set 200 buc", 6, "set", 45.50),
    ]),
    ("FVR-011", "vopsele-rapid", "2025-03-25", [
        ("Lac lemn mat 5L", 6, "buc", 86.80),
        ("Grund lemn 5L", 2, "buc", 68.00),
    ]),
    ("FVR-024", "vopsele-rapid", "2025-07-14", [
        ("Lac lemn mat 5L", 5, "buc", 86.80),
        ("Vopsea lavabila alba 10L", 3, "buc", 96.67),
    ]),
    ("FTN-005", "transport-nord", "2025-06-20", [
        ("Transport marfa Cluj-Napoca - santier", 1, "cursa", 620.00),
        ("Manipulare si incarcare", 1, "serv", 178.15),
    ]),
    ("FTN-013", "transport-nord", "2025-11-03", [
        ("Transport marfa Cluj-Napoca - santier", 1, "cursa", 620.00),
        ("Manipulare si incarcare", 1, "serv", 304.62),
    ]),
    ("AV-2025-018", "mobilier-deco", "2025-02-10", [
        ("Biblioteca lemn masiv la comanda", 2, "buc", 3150.00),
        ("Birou executiv lemn stejar", 3, "buc", 2483.33),
    ]),
    ("AV-2025-057", "mobilier-deco", "2025-06-25", [
        ("Mobilier showroom - set complet", 1, "set", 28500.00),
        ("Rafturi expunere lemn masiv", 10, "buc", 1470.00),
        ("Montaj si instalare la client", 1, "serv", 1600.00),
    ]),
    ("AV-2025-091", "mobilier-deco", "2025-10-15", [
        ("Birou executiv lemn stejar", 4, "buc", 2483.33),
        ("Rafturi expunere lemn masiv", 4, "buc", 1470.00),
    ]),
    ("AV-2025-042", "cabinet-ionescu", "2025-05-05", [
        ("Biblioteca birou avocatura lemn masiv", 1, "buc", 6800.00),
        ("Masa conferinta lemn masiv 10 persoane", 1, "buc", 3542.02),
    ]),
    ("AV-2025-071", "popescu-andrei", "2025-08-20", [
        ("Comoda lemn masiv", 1, "buc", 1890.00),
        ("Noptiera lemn masiv", 2, "buc", 780.25),
    ]),
]

TVA_RATE = 0.19

# Messy, real-world-style filenames for the flat "dump" folder — deliberately NOT
# type-prefixed or organized, since a real client drop-in won't be pre-sorted.
# Keyed by invoice id / contract-file-key / hr-file-key / email-file-key.
DUMP_NAMES = {
    "FLP-014": "Document_15012025.txt",
    "FLP-031": "atasament (1).txt",
    "FLP-052": "20.05.2025.txt",
    "FLP-061": "Document nou (2).txt",
    "FLP-078": "copie1.txt",
    "FLP-096": "octombrie.txt",
    "FFE-022": "factura feronerie.txt",
    "FFE-039": "fff.txt",
    "FFE-058": "Fwd - feronerie iunie.txt",
    "FFE-081": "Document nou.txt",
    "FVR-011": "chitanta vopsele martie.txt",
    "FVR-024": "vopsele iulie.txt",
    "FTN-005": "final.txt",
    "FTN-013": "transport nord noiembrie.txt",
    "AV-2025-018": "AV 2025 018.txt",
    "AV-2025-057": "comanda mobilier deco iunie.txt",
    "AV-2025-091": "Document (3).txt",
    "AV-2025-042": "factura ionescu.txt",
    "AV-2025-071": "chitanta popescu.txt",
}


def invoice_totals(items):
    subtotal = sum(round(q * pu, 2) for _, q, _, pu in items)
    tva = round(subtotal * TVA_RATE, 2)
    total = round(subtotal + tva, 2)
    return subtotal, tva, total


def render_invoice(inv_id, partner_key, date, items, kind):
    partner = PARTNERS[partner_key]
    subtotal, tva, total = invoice_totals(items)
    if kind == "cumparare":
        furnizor, cumparator = partner, COMPANY
    else:
        furnizor, cumparator = COMPANY, partner

    lines = []
    lines.append("FACTURA FISCALA")
    lines.append(f"Seria/Nr: {inv_id}")
    lines.append(f"Data emiterii: {date}")
    lines.append("")
    lines.append("FURNIZOR:")
    lines.append(f"  {furnizor['name']}")
    if isinstance(furnizor, dict) and 'cui' in furnizor:
        lines.append(f"  CUI: {furnizor['cui']}" + (f"  Reg. Com.: {furnizor.get('j','-')}" if furnizor.get('j') else ""))
        lines.append(f"  Adresa: {furnizor['address']}")
    lines.append("")
    lines.append("CUMPARATOR:")
    lines.append(f"  {cumparator['name']}")
    lines.append(f"  CUI: {cumparator['cui']}" + (f"  Reg. Com.: {cumparator.get('j','-')}" if cumparator.get('j') else ""))
    lines.append(f"  Adresa: {cumparator['address']}")
    lines.append("")
    lines.append("Nr. crt | Denumire produs/serviciu | Cant. | UM | Pret unitar (fara TVA) | Valoare (fara TVA)")
    for i, (desc, q, um, pu) in enumerate(items, start=1):
        val = round(q * pu, 2)
        lines.append(f"{i} | {desc} | {q} | {um} | {pu:.2f} RON | {val:.2f} RON")
    lines.append("")
    lines.append(f"Subtotal (fara TVA): {subtotal:.2f} RON")
    lines.append(f"TVA (19%): {tva:.2f} RON")
    lines.append(f"TOTAL DE PLATA: {total:.2f} RON")
    lines.append("Moneda: RON")
    lines.append("")
    lines.append("Modalitate de plata: Ordin de plata / Transfer bancar")
    lines.append(f"Termen de plata: 15 zile de la data emiterii")
    return "\n".join(lines) + "\n", total


def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


invoice_records = []  # for the accounting workbook + README ground truth
manifest = []  # one entry per file in dump/, for scoring classification/extraction

for inv_id, partner_key, date, items in INVOICES:
    kind = "cumparare" if PARTNERS[partner_key]["type"] == "furnizor" else "vanzare"
    text, total = render_invoice(inv_id, partner_key, date, items, kind)
    fname = f"dump/{DUMP_NAMES[inv_id]}"
    write(fname, text)
    invoice_records.append({
        "id": inv_id, "partner_key": partner_key, "partner": PARTNERS[partner_key]["name"],
        "date": date, "kind": kind, "total": total,
    })
    manifest.append({
        "filename": DUMP_NAMES[inv_id],
        # "category" is a broad ground-truth bucket used only for scoring/
        # reporting in the eval script - NOT a taxonomy fed to or enforced on
        # the classifier, which returns open-text document_type instead (see
        # backend/foldarai/schema.py).
        "category": "invoice",
        "contains_financial_data": True,
        "invoice_id": inv_id,
        "partner": PARTNERS[partner_key]["name"],
        "date": date,
        "direction": "purchase" if kind == "cumparare" else "sale",
        "total_amount_ron": total,
    })

print(f"Wrote {len(invoice_records)} invoice files.")

# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------
CONTRACTS = {
    "contract-lemn-prod.txt": """CONTRACT DE FURNIZARE Nr. 12/02.01.2025

Incheiat intre:
FURNIZOR: Lemn Prod SRL, CUI RO23456789, Reg. Com. J06/112/2015, cu sediul in
Str. Padurii nr. 5, Bistrita, jud. Bistrita-Nasaud, denumit in continuare "Furnizorul",

si

CUMPARATOR: Atelierul Verde SRL, CUI RO12345678, Reg. Com. J12/456/2018, cu sediul in
Str. Fabricii nr. 10, Cluj-Napoca, jud. Cluj, denumit in continuare "Cumparatorul".

Art. 1 - Obiectul contractului
Furnizorul se obliga sa livreze periodic Cumparatorului materie prima din lemn masiv
(panouri lemn masiv stejar/fag, cherestea rasinoase, furnir stejar) pe baza de comenzi
lansate in scris (email sau portal).

Art. 2 - Durata contractului
Prezentul contract este valabil de la 01.01.2025 pana la 31.12.2025, cu posibilitate
de prelungire prin act aditional.

Art. 3 - Termen de livrare
Furnizorul se obliga sa livreze marfa comandata in termen de maximum 5 (cinci) zile
lucratoare de la data lansarii comenzii.

Art. 4 - Penalitati
In caz de intarziere in livrare, Furnizorul datoreaza penalitati de 0,1% pe zi de
intarziere, calculate la valoarea comenzii intarziate, plafonate la maximum 10% din
valoarea comenzii respective.

Art. 5 - Modalitate de plata
Cumparatorul va achita facturile emise de Furnizor in termen de 15 zile de la data
emiterii facturii, prin ordin de plata.

Art. 6 - Incetare
Oricare dintre parti poate denunta unilateral contractul cu un preaviz scris de 30 zile.

Semnat astazi, 02.01.2025, la Cluj-Napoca, in doua exemplare originale.
""",
    "contract-feronerie-est.txt": """CONTRACT DE FURNIZARE Nr. 8/01.02.2025

Incheiat intre:
FURNIZOR: Feronerie Est SRL, CUI RO34567890, Reg. Com. J22/331/2016, cu sediul in
Str. Industriilor nr. 22, Iasi, jud. Iasi, denumit in continuare "Furnizorul",

si

CUMPARATOR: Atelierul Verde SRL, CUI RO12345678, Reg. Com. J12/456/2018, cu sediul in
Str. Fabricii nr. 10, Cluj-Napoca, jud. Cluj, denumit in continuare "Cumparatorul".

Art. 1 - Obiectul contractului
Furnizorul se obliga sa livreze feronerie si accesorii pentru mobilier (balamale,
glisiere sertar, manere, elemente de asamblare) conform comenzilor Cumparatorului.

Art. 2 - Durata contractului
Contractul este valabil de la 01.02.2025 pana la 31.01.2026.

Art. 3 - Termen de livrare
Termenul de livrare este de 3 (trei) zile lucratoare de la confirmarea comenzii.

Art. 4 - Modalitate de plata
Facturile se achita in termen de 30 zile de la data emiterii.

Art. 5 - Revizuire preturi
Preturile pot fi revizuite de Furnizor cu o notificare scrisa prealabila de minimum
30 de zile, transmisa Cumparatorului.

Art. 6 - Incetare
Contractul poate fi reziliat de oricare dintre parti cu un preaviz de 30 zile.

Semnat astazi, 01.02.2025, la Cluj-Napoca, in doua exemplare originale.
""",
    "contract-transport-nord.txt": """CONTRACT DE PRESTARI SERVICII DE TRANSPORT Nr. 4/01.03.2025

Incheiat intre:
PRESTATOR: Transport Nord SRL, CUI RO56789012, Reg. Com. J06/77/2014, cu sediul in
Str. Transportatorilor nr. 8, Bistrita, jud. Bistrita-Nasaud, denumit in continuare
"Prestatorul",

si

BENEFICIAR: Atelierul Verde SRL, CUI RO12345678, Reg. Com. J12/456/2018, cu sediul in
Str. Fabricii nr. 10, Cluj-Napoca, jud. Cluj, denumit in continuare "Beneficiarul".

Art. 1 - Obiectul contractului
Prestatorul asigura servicii de transport marfa (mobilier finit, materie prima) intre
depozitul Beneficiarului si santiere/clienti, la solicitarea Beneficiarului.

Art. 2 - Durata contractului
Contractul este valabil de la 01.03.2025 pana la 28.02.2026.

Art. 3 - Termen de executie
Prestatorul se obliga sa efectueze cursele solicitate in maximum 48 de ore de la
solicitare, cu exceptia curselor urgente convenite separat.

Art. 4 - Tarife si plata
Tarifele sunt cele din oferta anexata; facturile se achita in 15 zile de la emitere.

Art. 5 - Incetare
Contractul poate fi reziliat cu un preaviz de 15 zile de oricare dintre parti.

Semnat astazi, 01.03.2025, la Cluj-Napoca, in doua exemplare originale.
""",
    "contract-mobilier-deco.txt": """CONTRACT DE VANZARE-CUMPARARE MOBILIER LA COMANDA Nr. 21/05.02.2025

Incheiat intre:
VANZATOR: Atelierul Verde SRL, CUI RO12345678, Reg. Com. J12/456/2018, cu sediul in
Str. Fabricii nr. 10, Cluj-Napoca, jud. Cluj, denumit in continuare "Vanzatorul",

si

CUMPARATOR: Mobilier Deco SRL, CUI RO67890123, Reg. Com. J12/890/2017, cu sediul in
Str. Decoratorilor nr. 14, Cluj-Napoca, jud. Cluj, denumit in continuare "Cumparatorul".

Art. 1 - Obiectul contractului
Vanzatorul se obliga sa proiecteze, execute si livreze mobilier la comanda (birouri,
biblioteci, rafturi expunere, mobilier showroom) conform comenzilor si specificatiilor
transmise de Cumparator.

Art. 2 - Durata contractului
Contractul este valabil de la 05.02.2025 pana la 04.02.2026, cu posibilitate de
prelungire prin act aditional pentru comenzi recurente.

Art. 3 - Termen de executie
Vanzatorul se obliga sa execute si sa livreze fiecare comanda in maximum 30 de zile
lucratoare de la incasarea avansului de 50%.

Art. 4 - Garantie
Produsele livrate beneficiaza de o garantie de 24 de luni de la data receptiei,
acoperind defecte de material si de executie.

Art. 5 - Modalitate de plata
50% avans la lansarea comenzii, diferenta de 50% la livrare, in termen de 15 zile de
la data facturii.

Art. 6 - Incetare
Oricare dintre parti poate denunta contractul cu un preaviz scris de 30 zile, fara a
afecta comenzile deja confirmate si achitate cu avans.

Semnat astazi, 05.02.2025, la Cluj-Napoca, in doua exemplare originale.
""",
}

CONTRACT_DUMP_NAMES = {
    "contract-lemn-prod.txt": "Contract Lemn Prod 2025.txt",
    "contract-feronerie-est.txt": "contract feronerie SEMNAT.txt",
    "contract-transport-nord.txt": "Contract transport final v2.txt",
    "contract-mobilier-deco.txt": "contract mobilier deco - semnat.txt",
}
CONTRACT_ENTITY = {
    "contract-lemn-prod.txt": "Lemn Prod SRL",
    "contract-feronerie-est.txt": "Feronerie Est SRL",
    "contract-transport-nord.txt": "Transport Nord SRL",
    "contract-mobilier-deco.txt": "Mobilier Deco SRL",
}
for fname, content in CONTRACTS.items():
    dump_name = CONTRACT_DUMP_NAMES[fname]
    write(f"dump/{dump_name}", content)
    manifest.append({
        "filename": dump_name,
        "category": "contract",
        "contains_financial_data": False,
        "partner": CONTRACT_ENTITY[fname],
    })
print(f"Wrote {len(CONTRACTS)} contract files.")

# ---------------------------------------------------------------------------
# HR documents
# ---------------------------------------------------------------------------
HR = {
    "contract-munca-ioana-pop.txt": """CONTRACT INDIVIDUAL DE MUNCA Nr. 3/10.01.2023

Angajator: Atelierul Verde SRL, CUI RO12345678, cu sediul in Str. Fabricii nr. 10,
Cluj-Napoca, reprezentat prin administrator.

Salariat: Pop Ioana, CNP 2870512123499, domiciliata in Cluj-Napoca, Str. Zorilor nr. 21.

Art. 1 - Functia
Salariatul este angajat in functia de Tamplar, Cod COR 752302.

Art. 2 - Locul de munca
Atelierul de productie al angajatorului, Str. Fabricii nr. 10, Cluj-Napoca.

Art. 3 - Durata contractului
Contract pe perioada nedeterminata, incepand cu data de 10.01.2023.

Art. 4 - Timp de munca
Norma intreaga, 8 ore/zi, 40 ore/saptamana.

Art. 5 - Salarizare
Salariul de baza lunar brut este de 4200 RON, platibil pana la data de 10 a lunii
urmatoare.

Art. 6 - Concediu de odihna
21 de zile lucratoare anual.

Art. 7 - Perioada de preaviz
In cazul incetarii contractului din initiativa salariatului, perioada de preaviz este
de 20 de zile lucratoare. In cazul concedierii din motive care nu tin de persoana
salariatului, angajatorul acorda un preaviz de minimum 20 de zile lucratoare.

Art. 8 - Alte clauze
Salariatul beneficiaza de echipament de protectie a muncii asigurat de angajator.

Semnat astazi, 10.01.2023, la Cluj-Napoca.
""",
    "contract-munca-mihai-georgescu.txt": """CONTRACT INDIVIDUAL DE MUNCA Nr. 7/15.03.2024

Angajator: Atelierul Verde SRL, CUI RO12345678, cu sediul in Str. Fabricii nr. 10,
Cluj-Napoca, reprezentat prin administrator.

Salariat: Georgescu Mihai, CNP 1900823123488, domiciliat in Cluj-Napoca, Str. Aurel
Vlaicu nr. 9.

Art. 1 - Functia
Salariatul este angajat in functia de Agent vanzari, Cod COR 332203.

Art. 2 - Locul de munca
Sediul angajatorului si deplasari la clienti pe raza judetului Cluj si judetele
limitrofe.

Art. 3 - Durata contractului
Contract pe perioada nedeterminata, incepand cu data de 15.03.2024.

Art. 4 - Timp de munca
Norma intreaga, 8 ore/zi, 40 ore/saptamana.

Art. 5 - Salarizare
Salariul de baza lunar brut este de 3800 RON, la care se adauga un comision de 2%
din valoarea vanzarilor incheiate si incasate de salariat.

Art. 6 - Concediu de odihna
21 de zile lucratoare anual.

Art. 7 - Perioada de preaviz
Perioada de preaviz convenita de parti, aplicabila atat in cazul demisiei cat si al
concedierii din motive care nu tin de persoana salariatului, este de 30 de zile
lucratoare.

Art. 8 - Alte clauze
Salariatul beneficiaza de decontarea cheltuielilor de deplasare la clienti, conform
politicii interne a angajatorului.

Semnat astazi, 15.03.2024, la Cluj-Napoca.
""",
}

HR_DUMP_NAMES = {
    "contract-munca-ioana-pop.txt": "CIM Ioana Pop.txt",
    "contract-munca-mihai-georgescu.txt": "contract munca Mihai.txt",
}
HR_ENTITY = {
    "contract-munca-ioana-pop.txt": "Pop Ioana",
    "contract-munca-mihai-georgescu.txt": "Georgescu Mihai",
}
for fname, content in HR.items():
    dump_name = HR_DUMP_NAMES[fname]
    write(f"dump/{dump_name}", content)
    manifest.append({
        "filename": dump_name,
        "category": "hr_document",
        "contains_financial_data": False,
        "employee": HR_ENTITY[fname],
    })
print(f"Wrote {len(HR)} HR files.")

# ---------------------------------------------------------------------------
# Emails
# ---------------------------------------------------------------------------
EMAILS = {
    "email-feronerie-est-majorare-pret-2025-04-10.txt": """De la: Radu Manea <radu.manea@feronerie-est.ro>
Catre: Atelierul Verde SRL <comenzi@atelierulverde.ro>
Data: 10.04.2025 09:14
Subiect: Majorare preturi feronerie incepand cu 01.05.2025

Buna ziua,

Va informam ca, incepand cu data de 01.05.2025, preturile pentru balamale, glisiere
sertar si manere se majoreaza cu aproximativ 8%, ca urmare a cresterii costurilor cu
materia prima (otel si aluminiu).

Lista de preturi actualizata va fi transmisa pana pe 20.04.2025. Comenzile lansate
si confirmate pana la 30.04.2025 vor fi facturate la preturile actuale.

Va multumim pentru intelegere si ramanem la dispozitie pentru orice clarificari.

Cu stima,
Radu Manea
Departament Vanzari, Feronerie Est SRL

---

De la: Atelierul Verde SRL <comenzi@atelierulverde.ro>
Catre: Radu Manea <radu.manea@feronerie-est.ro>
Data: 11.04.2025 15:32
Subiect: RE: Majorare preturi feronerie incepand cu 01.05.2025

Buna ziua, domnule Manea,

Multumim pentru instiintare. Vom lansa o comanda mai mare pana la finalul lunii
aprilie pentru a beneficia de preturile actuale, avand in vedere si un proiect mai
mare programat pentru luna iunie.

Va rugam sa ne confirmati daca majorarea de 8% se aplica uniform pe toate produsele
sau doar pe cele din otel.

Cu stima,
Atelierul Verde SRL
""",
    "email-lemn-prod-intarziere-livrare-2025-05-19.txt": """De la: Comenzi Lemn Prod <comenzi@lemnprod.ro>
Catre: Atelierul Verde SRL <comenzi@atelierulverde.ro>
Data: 19.05.2025 11:02
Subiect: Intarziere livrare comanda din 16.05.2025

Buna ziua,

Va informam ca livrarea comenzii lansate pe 16.05.2025 (panouri lemn masiv stejar
25mm si lambriu brad) va intarzia cu aproximativ 2 zile fata de termenul contractual
de 5 zile lucratoare, din cauza unei defectiuni la linia de debitare.

Marfa va fi livrata pe 22.05.2025 in loc de 20.05.2025. Ne cerem scuze pentru
inconvenient si suntem dispusi sa discutam o compensare conform contractului.

Cu stima,
Departament Logistica, Lemn Prod SRL
""",
    "email-mobilier-deco-comanda-mare-2025-06-02.txt": """De la: Elena Radulescu <elena.radulescu@mobilierdeco.ro>
Catre: Atelierul Verde SRL <comenzi@atelierulverde.ro>
Data: 02.06.2025 10:47
Subiect: Confirmare comanda mobilier showroom nou - deschidere 28.06.2025

Buna ziua,

Va confirmam lansarea comenzii pentru mobilierul complet al noului nostru showroom
din Cluj-Napoca: set mobilier showroom, 10 rafturi de expunere din lemn masiv, plus
montaj si instalare la fata locului.

Deschiderea showroom-ului este programata pe 30.06.2025, asa ca avem nevoie de
livrare si montaj finalizate cel tarziu pe 27.06.2025. Va rugam sa ne confirmati ca
termenul poate fi respectat.

Avansul de 50% a fost transmis prin ordin de plata astazi.

Multumim pentru colaborare,
Elena Radulescu
Mobilier Deco SRL
""",
    "email-intern-plan-productie-iunie-2025-06-03.txt": """De la: Administrator <admin@atelierulverde.ro>
Catre: Ioana Pop <ioana.pop@atelierulverde.ro>
Data: 03.06.2025 08:30
Subiect: Plan productie - comanda mare Mobilier Deco (termen 27.06.2025)

Buna, Ioana,

Am confirmat comanda de la Mobilier Deco pentru showroom-ul nou - trebuie sa livram
si montam pana pe 27.06.2025.

Am lansat deja o comanda suplimentara de panouri lemn masiv stejar si furnir la
Lemn Prod, cu livrare estimata in prima saptamana din iunie. Te rog sa pregatesti
planul de productie pentru atelier astfel incat sa avem tot mobilierul gata pana pe
25.06.2025, ca sa ramana timp pentru montaj.

Ai nevoie de feronerie suplimentara pe langa stocul curent? Daca da, lansam comanda
la Feronerie Est saptamana aceasta.

Multumesc,
Administrator, Atelierul Verde SRL
""",
    "email-vopsele-rapid-oferta-2025-03-20.txt": """De la: Vanzari Vopsele Rapid <vanzari@vopselerapid.ro>
Catre: Atelierul Verde SRL <comenzi@atelierulverde.ro>
Data: 20.03.2025 14:05
Subiect: Oferta de pret - lac lemn mat si grund lemn

Buna ziua,

Ca urmare a solicitarii dumneavoastra, va transmitem oferta de pret pentru:
- Lac lemn mat 5L: 86,80 RON/buc (fara TVA)
- Grund lemn 5L: 68,00 RON/buc (fara TVA)

Oferta este valabila 30 de zile. Nu avem in acest moment un contract cadru cu
dumneavoastra - va putem factura direct pe baza de comanda si aviz de livrare, sau
va putem trimite spre semnare un contract cadru daca doriti colaborare pe termen
lung.

Cu stima,
Departament Vanzari, Vopsele Rapid SRL
""",
}

EMAIL_DUMP_NAMES = {
    "email-feronerie-est-majorare-pret-2025-04-10.txt": "Fwd Fwd majorare pret feronerie.txt",
    "email-lemn-prod-intarziere-livrare-2025-05-19.txt": "email lemn prod intarziere.txt",
    "email-mobilier-deco-comanda-mare-2025-06-02.txt": "RE comanda mobilier deco.txt",
    "email-intern-plan-productie-iunie-2025-06-03.txt": "plan productie iunie.txt",
    "email-vopsele-rapid-oferta-2025-03-20.txt": "oferta vopsele.txt",
}
EMAIL_ENTITY = {
    "email-feronerie-est-majorare-pret-2025-04-10.txt": "Feronerie Est SRL",
    "email-lemn-prod-intarziere-livrare-2025-05-19.txt": "Lemn Prod SRL",
    "email-mobilier-deco-comanda-mare-2025-06-02.txt": "Mobilier Deco SRL",
    "email-intern-plan-productie-iunie-2025-06-03.txt": "intern",
    "email-vopsele-rapid-oferta-2025-03-20.txt": "Vopsele Rapid SRL",
}
for fname, content in EMAILS.items():
    dump_name = EMAIL_DUMP_NAMES[fname]
    write(f"dump/{dump_name}", content)
    manifest.append({
        "filename": dump_name,
        "category": "email",
        "contains_financial_data": False,
        "partner": EMAIL_ENTITY[fname],
    })
print(f"Wrote {len(EMAILS)} email files.")

# ---------------------------------------------------------------------------
# Accounting spreadsheet (mirrors the invoices above)
# ---------------------------------------------------------------------------
wb = Workbook()
ws = wb.active
ws.title = "Registru facturi 2025"
headers = ["Nr. factura", "Tip", "Partener", "Data", "Total (RON, cu TVA)"]
ws.append(headers)
for cell in ws[1]:
    cell.font = Font(bold=True)

for rec in sorted(invoice_records, key=lambda r: r["date"]):
    tip = "Cumparare (cheltuiala)" if rec["kind"] == "cumparare" else "Vanzare (venit)"
    ws.append([rec["id"], tip, rec["partner"], rec["date"], rec["total"]])

for col, width in zip("ABCDE", [14, 24, 26, 12, 20]):
    ws.column_dimensions[col].width = width

accounting_fname = "Registru facturi 2025.xlsx"
os.makedirs(os.path.join(ROOT, "dump"), exist_ok=True)
wb.save(os.path.join(ROOT, "dump", accounting_fname))
manifest.append({
    "filename": accounting_fname,
    "category": "accounting_register",
    "contains_financial_data": True,
    "note": "Not one of the originally-illustrative MVP document types "
            "(contract/invoice/hr_document/email) - included specifically to "
            "test that classification is genuinely open-ended (document_type "
            "is free text) rather than forcing a bad fit into a fixed list.",
})
print(f"Wrote dump/{accounting_fname}")

with open(os.path.join(ROOT, "manifest.json"), "w", encoding="utf-8") as f:
    import json
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print(f"Wrote manifest.json with {len(manifest)} entries.")

# ---------------------------------------------------------------------------
# Ground-truth summary (for README + validation)
# ---------------------------------------------------------------------------
from collections import defaultdict

monthly = defaultdict(lambda: {"venituri": 0.0, "cheltuieli": 0.0})
by_partner_purchase = defaultdict(float)
all_totals = []
for rec in invoice_records:
    month = rec["date"][:7]
    all_totals.append(rec["total"])
    if rec["kind"] == "vanzare":
        monthly[month]["venituri"] += rec["total"]
    else:
        monthly[month]["cheltuieli"] += rec["total"]
        by_partner_purchase[rec["partner"]] += rec["total"]

print("\n--- Ground truth ---")
best_month, best_profit = None, None
for month in sorted(monthly):
    profit = monthly[month]["venituri"] - monthly[month]["cheltuieli"]
    print(f"{month}: venituri={monthly[month]['venituri']:.2f} cheltuieli={monthly[month]['cheltuieli']:.2f} profit={profit:.2f}")
    if best_profit is None or profit > best_profit:
        best_profit, best_month = profit, month
print(f"\nBest month: {best_month} (profit {best_profit:.2f} RON)")
print(f"Average invoice total: {sum(all_totals)/len(all_totals):.2f} RON over {len(all_totals)} invoices")
print("Total purchases by supplier:")
for p, v in by_partner_purchase.items():
    print(f"  {p}: {v:.2f} RON")
