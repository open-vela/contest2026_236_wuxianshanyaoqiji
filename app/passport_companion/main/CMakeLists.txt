idf_component_register(SRCS "main.c" "companion_ui.c" "companion_font.c" "companion_status_font.c" "companion_character.c"
    INCLUDE_DIRS "."
    REQUIRES bsp esp_event esp_netif esp_wifi esp_http_client nvs_flash json esp_timer)
