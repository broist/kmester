# KalóriaMester

Egy egyfelhasználós, mobilra optimalizált, önhostolt kalória- és tápanyag-napló. Napi étkezési naplót, gramm alapú számítást, saját ételeket, vonalkódos termékfelismerést és JSON exportot ad.

## Indítás Linux szerveren

Előfeltétel: Docker Engine és a Docker Compose plugin. Klónozd vagy másold fel ezt a könyvtárat a szerverre, majd:

```bash
cp .env.example .env
# szerkeszd a .env fájlt: kötelezően cseréld le az összes jelszót és az APP_SECRET-et
docker compose up -d --build
```

Ezután az app a `http://szerver:8080` címen elérhető. Az első belépéshez az `APP_USERNAME` és `APP_PASSWORD` értékeit használd. Nincs publikus regisztráció.

## HTTPS és reverse proxy

A frontend konténer a `HTTP_PORT` változóban megadott porton szolgál ki, és `/api/` alatt továbbítja a kéréseket a belső backendnek. Ezért Caddy vagy Nginx elé közvetlenül betehető. Kamera-hozzáférés éles mobilos használathoz **HTTPS-t igényel** (a `localhost` fejlesztési kivétel).

Caddy példa:

```caddy
kaloria.example.com {
  reverse_proxy 127.0.0.1:8080
}
```

Állítsd az `APP_URL`-t a tényleges, HTTPS-es URL-re, majd indítsd újra: `docker compose up -d`. Caddy automatikusan kezeli a tanúsítványt, ha a domain DNS-e a szerverre mutat és a 80/443-as port elérhető.

## Adat és mentés

Az adatbázis a `postgres_data` Docker volume-ban perzisztens. Rendszeres, hordozható PostgreSQL mentéshez:

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > kaloriamester-$(date +%F).sql
```

Az alkalmazásból JSON export is lekérhető belépve: `GET /api/export` (például a böngésző fejlesztői eszközeiből vagy egy hitelesített klienssel). Az SQL mentést tartsd a szervertől külön helyen is.

## Vonalkód és adatminőség

Az étel hozzáadásánál a **Beolvasás** gomb mobil kamerát kér, és ZXing fallbackkel olvassa az EAN-13, EAN-8, UPC-A, UPC-E típusokat. Sikeres olvasás után rezgésjelzés van, ha a telefon támogatja.

A terméket a saját gyorsítótárból, hiány esetén az Open Food Facts aktuális v3 termék-vonalkód végpontjáról kéri le. Csak a szükséges mezőket tölti le, az azonosító `User-Agent` az `.env`-ben állítható. A külső találatot a saját adatbázisba menti; a már importált termék kézzel szerkeszthető, és szerkesztés után `verified_by_user=true`, tehát új külső lekérés nem írja felül. Hiányzó kötelező makrók esetén az adat `hiányos` jelölést kap. Nem találatkor automatikusan kitöltött vonalkóddal nyitható saját étel űrlap.

Az Open Food Facts a terméklekéréshez jelenleg a v3 API-t javasolja; a v2 új integrációhoz elavult. Lásd a hivatalos [API áttekintést](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/) és a [termék lekérési referenciaoldalt](https://openfoodfacts.github.io/documentation/docs/Product-Opener/v3/products/get-api-v3-product-code/).

## Fejlesztés és ellenőrzés

```bash
cd frontend && npm install && npm run build
docker compose up --build
```

Backend egységtesztek a tápértékarányosítás alapképleteit fedik le a konténerben: `docker compose exec backend pytest`.

## Következő érdemi bővítések

Receptek/adagok és kész súly kezelése, víz- és testsúlynapló, célbeállítások, heti átlagok, valamint teljes PWA/offline támogatás még nincs elkészítve. A jelenlegi verzió a gyors, ellenőrzött ételrögzítésre és a vonalkódos saját termékkatalógusra koncentrál.
