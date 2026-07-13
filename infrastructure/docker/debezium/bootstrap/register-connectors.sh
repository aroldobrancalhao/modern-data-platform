#!/bin/sh

set -e

echo "==================================="
echo "Platform Init"
echo "==================================="

echo "Waiting Debezium..."

until curl -fs http://debezium-connect:8083/connectors >/dev/null
do
    sleep 2
done

echo "Debezium Ready"

for FILE in /connectors/*.json
do

    NAME=$(jq -r '.name' "$FILE")

    echo "Checking connector: $NAME"

    HTTP_CODE=$(curl \
        -s \
        -o /dev/null \
        -w "%{http_code}" \
        http://debezium-connect:8083/connectors/$NAME)

    if [ "$HTTP_CODE" = "200" ]; then

        echo "Updating $NAME"

        jq '.config' "$FILE" | \
        curl \
            -s \
            -X PUT \
            -H "Content-Type: application/json" \
            --data @- \
            http://debezium-connect:8083/connectors/$NAME/config

    else

        echo "Creating $NAME"

        curl \
            -s \
            -X POST \
            -H "Content-Type: application/json" \
            --data @"$FILE" \
            http://debezium-connect:8083/connectors

    fi

done

echo "Finished."