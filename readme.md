# bbc-forwarder

project info | details
------------ | ------
auteur(s)    | l.c.vriend
afdeling     | csa
release      | 0.2
status       | dev.

## Instructie

```python script_bbc_forwarder.py```

## Use-case
Tussen de instellingen is afgesproken dat de verklaring bewijs betaald collegegeld (bbc) onderling digitaal uitgewisseld mag worden. Een gevolg van deze afspraak is dat *alle* bbc's via een centraal e-mailadres binnen zullen komen -- ook de bbc's voor studenten met een decentrale inschrijving. Deze bbc's zijn voor de faculteiten bestemd en moeten vanuit centraal doorgezet worden.

De verwachting is dat er in de loop van de inschrijfcampagne honderden voor de faculteit bestemde bbc's zullen binnenkomen. Het doorzetten van deze bbc's vergt uitzoekwerk. Bovendien komt het voor dat bbc's niet direct gekoppeld kunnen worden aan een inschrijving. In dat geval moet periodiek gecontroleerd worden of de bbc inmiddels verwerkt kan worden.

De bbc-forwarder heeft als doel om dit arbeidsintensieve proces te automatiseren. Daarbij gaat de robot op hoofdlijnen als volgt te werk:

1. Lees de mailbox uit waar de bbc's binnenkomen.
2. Kijk per message in de mailbox of er een of meerdere pdf-attachments aanwezig zijn en parse deze.
3. Zoek binnen de geparste pdf's naar geboortedata en gebruik deze om in de studentendatabase een serie kandidaten voor te selecteren.
4. Zoek vervolgens binnen de pdf naar de aanwezigheid van de achternaam van de gevonden kandidaten.
5. Indien het mogelijk is om een bbc aan een student te koppelen, controleer dan of het een student betreft met een centrale of decentrale inschrijving:

    * Bij een decentrale inschrijving: stel een e-mail op met aanvullende informatie (studentnummer, bedrag, etc.) aan de betreffende faculteit en forward de pdf.
    * Bij een centrale inschrijving: stel dan een e-mail op met aanvullende informatie (studentnummer, bedrag, etc.) en verwerkingsinstructie en verplaats deze vervolgens naar de map met te verwerken bbc's.

## Afhankelijkheden

### API
- [Microsoft Graph](https://docs.microsoft.com/en-us/graph/overview?view=graph-rest-1.0) - Gateway to data and intelligence in Microsoft 365
- [Microsoft Azure app-service](https://docs.microsoft.com/en-us/azure/app-service/) - build and host web apps, mobile back ends, and RESTful APIs in the programming language of your choice without managing infrastructure

### Externe libraries
- [O365](https://github.com/O365/python-o365) - Microsoft Graph and Office 365 API made easy
- [Pdfminer.six](https://pdfminersix.readthedocs.io/en/latest/) - python package for extracting information from PDF documents
- [pandas](pandas.pydata.org/) - fast, powerful, flexible and easy to use open source data analysis and manipulation tool

### Eigen libraries
- [OSIRIS-query](https://github.com/uu-csa/osiris_query) - Platform voor queries uit OSIRIS

### Datasets
- Inschrijfhistorie centrale/decentrale inschrijfregels uit OSIRIS
- Lijst met facultaire e-mailadressen
- Lijst met bbc e-mailadressen van andere instellingen

## Project structuur

```
bbc_forwarder
|
|__/bbc_forwarder (code)
|   |_ config.py     : inladen configuratie bestand
|   |_ forwarder.py  : logica voor annoteren/forwarden e-mails
|   |_ mailbox.py    : toegang tot mailbox en mappenstructuur
|   |_ parser.py     : parser voor pdf's in e-mails en logging
|   |_ population.py : inladen en prepareren populatie database
|   |_ templates.py  : inladen e-mail templates en subject lines
|
|__/logs (opslagplaats voor log-bestanden)
|
|__/static (opslaagplaats voor flowcharts)
|
|__/templates (opslagplaats voor e-mail templates)
|   |_ template._base_.html    : basis layout
|   |_ template.annotated.html : eigen annotaties
|   |_ template.forward.html   : forwards aan faculteit
|   |_ template.issues.html    : issues
|   |_ template.logs.html      : logs
|
|__/tests (code : unittests)
|
|___config.example.json : voorbeeld configuratie bestand
|   ('config.json' inrichten voor productie)
|
|___environment.yml : systeem afhankelijkheden
|
|___flowchart_parser.drawio : [drawio](https://app.diagrams.net/) bron flowcharts
|
|___readme.md : deze toelichting
|
|___script_bbc_forwarder.py : script om de routine uit te voeren
```

## Sanity checks
De volgende sanity checks zijn in het systeem ingebouwd:

- [ ] Inschrijfhistorie ouder dan vandaag > foutmelding
- [x] Mappenstructuur binnen de verwerkingsmap gewijzigd > foutmelding
- [x] E-mail bevat meer dan één pdf > naar handmatige afhandeling
- [x] Geen enkele record gekoppeld aan document > naar handmatige afhandeling
- [x] Meer dan één record gekoppeld aan document > naar handmatige afhandeling

## Risico taxatie
### Risico als het systeem uitvalt
Het systeem verwerkt e-mails automatisch. De verwerking bestaat uit het annoteren van de mail en het doorsturen ervan. Indien het systeem uitvalt, kan de verwerking alsnog handmatig worden uitgevoerd.

### Risico bij verkeerde verwerking
Het systeem matcht studenten via een twee-ledige routine. Er kunnen hierbij twee soorten fouten optreden:

1. Een student is aanwezig in de database maar wordt niet gematcht.
2. Het systeem matcht de verkeerde student aan de e-mail.

**Aanwezige student wordt niet gematcht**

De kans op dit type fout is het grootst. Deze fout kan optreden indien de aanleverende instelling een fout heeft gemaakt in de spelling van de naam of in de geboortedatum. Daarnaast is het mogelijk dat bepaalde diakrieten in de naam het matchen bemoeilijken (indien dit een issue blijkt te zijn, kan hier aanvullende functionaliteit voor worden ontwikkeld).

Het gevolg van deze fout is dat de bbc onterecht in de te verwerken map blijft. Dit betekent dat er alsnog periodiek een handmatige controle zal moeten plaatsvinden op de bbc's die langere tijd onverwerkt blijven.

**Verkeerde student wordt gematcht**

De kans op dit type fout is zeer klein. Deze fout kan optreden in het geval dat de eigenlijke student niet gematcht wordt en er een andere student bestaat met dezelfde geboortedatum die een achternaam heeft die voorkomt in de pdf (c.q. de achternaam komt overeen met degene die de bbc ondertekend heeft).
In het onwaarschijnlijke geval dat dit issue zich voordoet, geldt dat het doorsturen alleen intern naar vastgelegde uu-adressen gebeurt. In de e-mailtekst wordt de ontvangers gewezen op wat zij kunnen doen indien er iets niet klopt: CSa informeren. Omdat de student toestemming heeft gegeven aan de instellingen om de bbc te verwerken, bestaat er ook geen privacy risico.

## Proces flow
### Verwerking message
![process_message](static/process_message.svg)

### Verwerking parsed tekst van pdf
![process_parsed_text](static/process_parsed_text.svg)

### Verwerking zoek resultaten
![process_search_results](static/process_search_results.svg)

## To do

### Documentatie
- [x] use-case
- [x] risico taxatie
- [x] projectstructuur
- [x] algemene documentatie
- [x] documentatie op module niveau
- [x] documentatie op code niveau (functies, variabelen en objecten)
- [x] flowcharts van de processtructuur
- [ ] gebruikersinstructie

### Kwaliteitseisen
- [x] configuratie
- [x] modulaire opbouw
- [x] killswitch
- [x] logging
- [x] sanity checks
- [x] unit tests

### Overige standaarden
- [x] versiebeheer
- [ ] ketentest
