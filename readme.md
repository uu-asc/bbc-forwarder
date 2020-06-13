# bbc-forwarder
auteur: l.c.vriend

## Use-case
Tussen de instellingen is afgesproken dat de verklaring bewijs betaald collegegeld (bbc) onderling digitaal uitgewisseld mag worden. Een gevolg van deze afspraak is dat *alle* bbc's via een centraal e-mailadres binnen zullen komen -- ook de bbc's voor studenten met een decentrale inschrijving.

Het doorzetten van deze bbc's vergt veel uitzoekwerk. Bovendien komt het voor dat bbc's niet direct gekoppeld kunnen worden aan een inschrijving. In dat geval moet periodiek gecontroleerd worden of de bbc inmiddels verwerkt kan worden.

De bbc-forwarder heeft als doel om dit arbeidsintensieve proces te automatiseren. Daarbij gaat de robot op hoofdlijnen als volgt te werk:

1. Lees de mailbox uit waar de bbc's binnenkomen.
2. Kijk per message in de mailbox of er een of meerdere pdf-attachments aanwezig zijn en parse deze.
3. Zoek binnen de geparste pdf's naar geboortedata en gebruik deze om in de studentendatabase een serie kandidaten voor te selecteren.
4. Zoek vervolgens binnen de pdf naar de aanwezigheid van de achternaam van de gevonden kandidaten.
5. Indien het mogelijk is om een bbc aan een student te koppelen, controleer dan of het een student betreft met een centrale of decentrale inschrijving:

    * Bij een decentrale inschrijving: stel een e-mail op aan de betreffende faculteit een forward de pdf.
    * Bij een centrale inschrijving: voeg meta-informatie toe aan de e-mail en plaats deze vervolgens in de map met te verwerken bbc's. 

## To do

### Documentatie
- []  algemene documentatie
- [x] module documentatie
- [x] code documentatie
- []  flowcharts

### Kwaliteitseisen
- [x] versiebeheer
- [x] logging
- []  sanity checks
- [x] unit tests
- []  ketentest

## Proces flow
### Verwerking message
![process_message](static/process_message.svg)

### Verwerking parsed tekst van pdf
![process_parsed_text](static/process_parsed_text.svg)
