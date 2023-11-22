#!/bin/sh

sed 's/<Тип>ExchangePlan<\/Тип>/<Тип>ПланОбмена<\/Тип>/g' conf-eng.xml > conf-ru.xml
sed -i 's/<Тип>Catalog<\/Тип>/<Тип>Справочник<\/Тип>/g' conf-ru.xml
sed -i 's/<Тип>Document<\/Тип>/<Тип>Документ<\/Тип>/g' conf-ru.xml
sed -i 's/<Тип>Enum<\/Тип>/<Тип>Перечисление<\/Тип>/g' conf-ru.xml
sed -i 's/<Тип>ChartOfCharacteristicTypes<\/Тип>/<Тип>ПланВидовХарактеристик<\/Тип>/g' conf-ru.xml
sed -i 's/<Тип>ChartOfAccounts<\/Тип>/<Тип>ПланСчетов<\/Тип>/g' conf-ru.xml
sed -i 's/<Тип>InformationRegister<\/Тип>/<Тип>РегистрСведений<\/Тип>/g' conf-ru.xml
sed -i 's/<Тип>AccumulationRegister<\/Тип>/<Тип>РегистрНакопления<\/Тип>/g' conf-ru.xml
sed -i 's/<Тип>AccountingRegister<\/Тип>/<Тип>РегистрБухгалтерии<\/Тип>/g' conf-ru.xml




