# A/B testavimo demonstracija

Mini A/B testavimo projektas, skirtas praktiškai parodyti, kaip veikia visas eksperimentas: nuo vartotojų paskirstymo į A ir B grupes iki statistinio rezultatų įvertinimo.

Projektas sukurtas pristatymui **„A/B testavimo procesas ir vertinimas“**.

> **Svarbu:** naudojamas sintetinis vartotojų srautas. Šis projektas demonstruoja A/B testavimo procesą ir statistiką, tačiau neįrodo, kad realūs žmonės elgtųsi taip pat.

## Kas testuojama?

Keičiamas tik vienas puslapio elementas – pagrindinio mygtuko (CTA) tekstas:

- **Variantas A:** `Learn more`
- **Variantas B:** `Start free trial`

Kiekvienas naujas vartotojas atsitiktinai priskiriamas vienam variantui. Tas pats vartotojas, kol turi tą patį slapuką (cookie), išlieka toje pačioje grupėje.

CTA paspaudimas vienam vartotojui registruojamas tik vieną kartą.

## Kaip veikia eksperimentas?

```text
Virtualus arba realus lankytojas
              ↓
      atsitiktinis A/B paskirstymas
              ↓
        A                 B
   Learn more      Start free trial
        \               /
         \             /
          click / no click
                ↓
          SQLite duomenys
                ↓
        statistinė analizė
                ↓
             Dashboard
```

## Reikalavimai

- Python 3.9+ rekomenduojamas
- Papildomų Python paketų diegti nereikia

Projektas naudoja tik Python standartinę biblioteką ir SQLite.

## Projekto struktūra

```text
ab_test_demo/
├── app.py                  # Web serveris, A/B randomizacija ir statistika
├── simulate.py             # Sintetinio srauto generatorius
├── requirements.txt        # Papildomų paketų nereikia
├── templates/
│   ├── landing.html        # Testuojamas landing page
│   └── dashboard.html      # Rezultatų dashboard
├── static/
│   └── style.css           # Puslapių stilius
└── README.md
```

Paleidus projektą automatiškai sukuriamas `ab_test.db` SQLite failas su eksperimento duomenimis.

## Greitas paleidimas

### 1. Paleisk A/B serverį

Pirmame terminale:

```bash
cd ab_test_demo
python3 app.py
```

Windows aplinkoje, jei `python3` neveikia:

```bash
python app.py
```

Serveris bus pasiekiamas adresu:

- Landing page: http://127.0.0.1:5000
- Dashboard: http://127.0.0.1:5000/dashboard

### 2. Sugeneruok sintetinį srautą

Antrame terminale:

```bash
cd ab_test_demo
python3 simulate.py --users 1000 --effect 0.03 --seed 42
```

Windows:

```bash
python simulate.py --users 1000 --effect 0.03 --seed 42
```

Dashboard atsinaujina automatiškai kas sekundę, todėl rezultatų pokyčius galima stebėti gyvai.

## Simuliatoriaus parametrai

### `--users`

Kiek virtualių vartotojų sugeneruoti.

```bash
--users 3000
```

reiškia, kad simuliacijoje dalyvaus 3000 lankytojų.

### `--effect`

Dirbtinai nustatytas **tikrasis B varianto poveikis** sintetinėje aplinkoje.

```bash
--effect 0.03
```

reiškia **+3 procentinių punktų** konversijos tikimybę B variantui.

Pavyzdžiui, jei konkrečios personos bazinė konversija yra 14 %:

```text
A = 14 %
B = 17 %
```

Svarbu: `effect` nėra A/B testo rezultatas. Tai iš anksto simuliacijoje nustatytas efektas, kurį vėliau bandome aptikti statistiniu testu.

### `--seed`

Leidžia pakartoti tą pačią atsitiktinę simuliaciją.

```bash
--seed 42
```

Naudojant tą patį `seed` ir tuos pačius parametrus gaunami atkartojami rezultatai.

## Virtualių vartotojų modelis

Kad visi sintetiniai vartotojai nebūtų vienodi, kiekvienam prieš A/B randomizaciją parenkama viena persona:

| Persona | Bazinė konversijos tikimybė |
|---|---:|
| Studentas | 9 % |
| Užimtas profesionalas | 14 % |
| Smulkaus verslo savininkas | 17 % |
| Kainai jautrus vartotojas | 8 % |
| Naujoves mėgstantis vartotojas (`early adopter`) | 20 % |

Šios tikimybės yra **mokomosios, sintetinės reikšmės**, o ne realaus vartotojų tyrimo duomenys.

Pirmiausia parenkama persona, o tik tada serveris nepriklausomai randomizuoja vartotoją į A arba B. Taip abi grupės gauna vartotojus iš to paties personų rinkinio.

## Ką rodo Dashboard?

Dashboard apskaičiuoja:

- A ir B lankytojų skaičių;
- A ir B paspaudimų skaičių;
- A ir B konversijos rodiklį (`conversion rate`);
- absoliutų konversijų skirtumą;
- santykinį pokytį (`relative lift`);
- dviejų proporcijų z-testą;
- dvipusį `p-value`;
- 95 % pasikliautinąjį intervalą (`95% CI`);
- ar rezultatas statistiškai reikšmingas pagal `α = 0.05`.

### Trumpa metrikų interpretacija

Tarkime:

```text
A = 10 %
B = 12 %
```

Tuomet:

- **absoliutus skirtumas:** `+2 procentiniai punktai`;
- **relative lift:** `+20 %`;
- jei `p < 0.05`, skirtumas pagal pasirinktą ribą laikomas statistiškai reikšmingu;
- jei 95 % CI apima `0`, duomenys vis dar suderinami su scenarijumi, kuriame tikro skirtumo nėra.

Statistinis reikšmingumas savaime nereiškia, kad pakeitimas yra praktiškai vertingas.

## Rekomenduojami demonstracijos scenarijai

### 1. H₀ scenarijus – tikro efekto nėra

```bash
python3 simulate.py --users 2000 --effect 0 --seed 42
```

Čia A ir B sintetinėje realybėje yra vienodi.

Tikslas – parodyti, kad net ir esant `effect = 0`, dėl atsitiktinio svyravimo dashboard gali rodyti skirtingas A ir B konversijas. Vien didesnio procento nepakanka išvadai apie tikrą poveikį.

### 2. Scenarijus su tikru B efektu

Dashboard paspausk **Reset experiment**, tada paleisk:

```bash
python3 simulate.py --users 3000 --effect 0.03 --seed 42
```

Čia B variantui sintetinėje aplinkoje pridedamas **+3 procentinių punktų** efektas.

Tikslas – parodyti, kaip surinkus pakankamai duomenų statistinis testas gali aptikti modelyje egzistuojantį skirtumą.

## Kaip parodyti realų A/B paskirstymą?

1. Atidaryk http://127.0.0.1:5000 Incognito / Private lange.
2. Puslapyje bus parodytas A arba B variantas.
3. Atidaryk naują privatų naršymo kontekstą, kad būtų sukurtas naujas vartotojas.
4. Pakartok, kol pamatysi kitą variantą.
5. Atidaryk Dashboard ir stebėk, kaip registruojami lankytojai bei paspaudimai.

## Eksperimento ribojimai

Šis projektas nėra realaus produkto A/B tyrimas.

Sintetinėje simuliacijoje:

- personų konversijos tikimybės nustatytos rankiniu būdu;
- `--effect` parametru galime patys nustatyti tikrą B poveikį;
- virtualūs vartotojai neturi realios žmogaus motyvacijos ar elgsenos;
- rezultatai negali būti naudojami kaip įrodymas, kad `Start free trial` realiems vartotojams yra geresnis už `Learn more`.

Projekto tikslas – **parodyti visą A/B testavimo grandinę**: randomizaciją, įvykių registravimą, konversijų skaičiavimą ir statistinį rezultatų vertinimą.

## Naudotos technologijos

- Python
- `http.server`
- SQLite
- HTML / CSS / JavaScript
- dviejų proporcijų z-testas
- 95 % pasikliautinasis intervalas

## Pastaba dėl Git

Duomenų bazė `ab_test.db` yra sugeneruojama paleidus projektą ir neturėtų būti keliama į Git repozitoriją. Tam pridedamas `.gitignore` failas.
