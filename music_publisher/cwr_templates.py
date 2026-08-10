"""Django templates for CWR generation."""

from django.template import Template

TEMPLATES_21 = {
    "HDR": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        'HDRPB{{ ipi_name_number|rjust:11|slice:"2:" }}'
        "{{ name|ljust:45 }}01.10"
        '{{ creation_date|date:"Ymd" }}'
        '{{ creation_date|date:"His" }}'
        '{{ creation_date|date:"Ymd" }}'
        "               \r\n{% endautoescape %}"
    ),
    "HDR_8": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "HDR{{ ipi_name_number|rjust:11 }}"
        "{{ name|ljust:45 }}01.10"
        '{{ creation_date|date:"Ymd" }}'
        '{{ creation_date|date:"His" }}'
        '{{ creation_date|date:"Ymd" }}'
        "               \r\n{% endautoescape %}"
    ),
    "GRH": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "GRH{{ transaction_type|ljust:3 }}0000102.10"
        "0000000000  \r\n{% endautoescape %}"
    ),
    "WRK": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "{{ record_type }}"
        "{{ transaction_sequence|rjust:8 }}00000000"
        "{{ work_title|ljust:60 }}  {{ code|ljust:14 }}"
        "{{ iswc|ljust:11 }}00000000            UNC"
        '{{ duration|date:"His"|default:"000000" }}{{ recorded_indicator }}'
        "      {{ version_type }}  "
        + " " * 40
        + "N00000000000"
        + " " * 51
        + "N"
        "\r\n{% endautoescape %}"
    ),
    "SPU": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "SPU{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}"
        "{{ chain_sequence|rjust:2 }}"
        "{{ cwr_code|default:code|ljust:9 }}"
        "{{ name|ljust:45 }}"
        " "
        "{{ role|default:'E '|ljust:2 }}"
        "{{ tax_id|default:'         '|ljust:9 }}"
        "{{ ipi_name_number|rjust:11 }}"
        "              "
        "{{ pr_society|soc }}{{ pr_share|default:0|cwrshare }}"
        "{{ mr_society|soc }}{{ mr_share|default:0|cwrshare }}"
        "{{ sr_society|soc }}{{ sr_share|default:0|cwrshare }}"
        + " " * 46
        + "\r\n{% endautoescape %}"
    ),
    "SWT": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "SWT{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}"
        "{{ cwr_code|default:code|ljust:9 }}"
        "{{ collection_pr_share|default:0|cwrshare }}"
        "{{ collection_mr_share|default:0|cwrshare }}"
        "{{ collection_sr_share|default:0|cwrshare }}"
        "I{{ territory_code|default:'0032'|ljust:4 }}"
        "{{ shares_change|default:' '|ljust:1 }}"
        "{{ territory_sequence|default:'001'|ljust:3 }}"
        "\r\n{% endautoescape %}"
    ),
    "SWR": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "SWR{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}"
        "{{ cwr_code|default:code|ljust:9 }}"
        "{{ last_name|ljust:45 }}"
        "{{ first_name|ljust:30 }}"
        " "
        "{{ writer_role|ljust:2 }}"
        "{{ tax_id|default:'         '|ljust:9 }}"
        "{{ ipi_name_number|rjust:11 }}"
        "{{ pr_society|soc }}{{ pr_share|default:0|cwrshare }}"
        "{{ mr_society|soc }}{{ mr_share|default:0|cwrshare }}"
        "{{ sr_society|soc }}{{ sr_share|default:0|cwrshare }}"
        + " " * 17
        + "{{ personal_number|default:'000000000000'|ljust:12 }}"
        " \r\n{% endautoescape %}"
    ),
    "SWT": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "SWT{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}"
        "{{ cwr_code|default:code|ljust:9 }}"
        "{{ collection_pr_share|default:pr_share|default:0|cwrshare }}"
        "{{ collection_mr_share|default:mr_share|default:0|cwrshare }}"
        "{{ collection_sr_share|default:sr_share|default:0|cwrshare }}"
        "I{{ territory_code|default:'0032'|ljust:4 }}"
        "{{ shares_change|default:' '|ljust:1 }}"
        "{{ territory_sequence|default:'001'|ljust:3 }}"
        "\r\n{% endautoescape %}"
    ),
    "PWR": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "PWR{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}"
        "{{ publisher_cwr_code|default:publisher_code|ljust:9 }}"
        "{{ publisher_name|ljust:45 }}"
        "{{ submitter_agreement_number|default:''|ljust:14 }}"
        "{{ society_assigned_agreement_number|default:''|ljust:14 }}"
        "{{ cwr_code|default:code|ljust:9 }}"
        "\r\n{% endautoescape %}"
    ),
    "OPU": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "OPU{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}{{ sequence|rjust:2 }}"
        + " " * 54
        + "YE 00000000000000000000              "
        "   {{ pr_share|default:0|cwrshare }}"
        "   {{ mr_share|default:0|cwrshare }}"
        "   {{ sr_share|default:0|cwrshare }}"
        " N                                             "
        "\r\n{% endautoescape %}"
    ),
    "OWR": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "OWR{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}{{ cwr_code|default:code|ljust:9 }}"
        "{{ last_name|ljust:45 }}{{ first_name|ljust:30 }}"
        '{{ writer_unknown_indicator|default:" " }}'
        "{{ writer_role|ljust:2 }}"
        "{{ tax_id|default:'         '|ljust:9 }}"
        "{{ ipi_name_number|rjust:11 }}"
        "{{ pr_society|soc }}{{ pr_share|default:0|cwrshare }}"
        "{{ mr_society|soc }}{{ mr_share|default:0|cwrshare }}"
        "{{ sr_society|soc }}{{ sr_share|default:0|cwrshare }}"
        + " " * 31
        + "\r\n{% endautoescape %}"
    ),
    "ALT": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "ALT{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}{{ alternate_title|ljust:60 }}"
        "{{ title_type|ljust:2 }}  \r\n{% endautoescape %}"
    ),
    "OWK": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "VER{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}{{ work_title|ljust:60 }}"
        + " " * (11 + 2 + 45 + 30 + 60 + 11 + 13 + 45 + 30 + 11 + 13 + 14)
        + "\r\n{% endautoescape %}"
    ),
    "PER": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "PER{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}{{ last_name|ljust:45 }}"
        "{{ first_name|ljust:30 }}                        \r\n"
        "{% endautoescape %}"
    ),
    "REC": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "REC{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}"
        '{{ release_date|default:"00000000" }}'
        + " " * 60
        + '{{ duration|rjust:6|default:"000000" }}     '
        + " " * 151
        + "{{ isrc|ljust:12 }}     \r\n{% endautoescape %}"
    ),
    "ORN": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "ORN{{ transaction_sequence|rjust:8 }}"
        "{{ record_sequence|rjust:8 }}LIB"
        + " " * 60
        + "{{ cd_identifier|ljust:15 }}0000{{ library|ljust:60 }}"
        + " " * (26 + 12 + 60 + 20)
        + "0000                  \r\n"
        "{% endautoescape %}"
    ),
    "GRT": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "GRT00001{{ transaction_count|rjust:8 }}"
        "{{ record_count|rjust:8 }}   0000000000\r\n{% endautoescape %}"
    ),
    "TRL": Template(
        "{% load cwr_generators %}{% autoescape off %}"
        "TRL00001{{ transaction_count|rjust:8 }}"
        "{{ record_count|rjust:8 }}{% endautoescape %}"
    ),
    "OPT": Template(""),
    "OWT": Template(""),
    "XRF": Template(""),
    "MAN": Template(""),
}

TEMPLATES_22 = TEMPLATES_21.copy()
TEMPLATES_22.update(
    {
        "HDR": Template(
            "{% load cwr_generators %}{% autoescape off %}"
            'HDRPB{{ ipi_name_number|rjust:11|slice:"2:" }}'
            "{{ name|ljust:45 }}01.10"
            '{{ creation_date|date:"Ymd" }}'
            '{{ creation_date|date:"His" }}'
            '{{ creation_date|date:"Ymd" }}'
            "               2.2002{{ settings.SOFTWARE|ljust:30 }}"
            "{{ settings.SOFTWARE_VERSION|ljust:30 }}\r\n{% endautoescape %}"
        ),
        "HDR_8": Template(
            "{% load cwr_generators %}{% autoescape off %}"
            "HDR{{ ipi_name_number|rjust:11 }}"
            "{{ name|ljust:45 }}01.10"
            '{{ creation_date|date:"Ymd" }}'
            '{{ creation_date|date:"His" }}'
            '{{ creation_date|date:"Ymd" }}'
            "               2.2002{{ settings.SOFTWARE|ljust:30 }}"
            "{{ settings.SOFTWARE_VERSION|ljust:30 }}\r\n{% endautoescape %}"
        ),
        "GRH": Template(
            "{% load cwr_generators %}{% autoescape off %}"
            "GRH{{ transaction_type|ljust:3 }}0000102.20"
            "0000000000  \r\n{% endautoescape %}"
        ),
        "PWR": Template(
            "{% load cwr_generators %}{% autoescape off %}"
            "PWR{{ transaction_sequence|rjust:8 }}"
            "{{ record_sequence|rjust:8 }}"
            "{{ publisher_cwr_code|default:publisher_code|ljust:9 }}"
            "{{ publisher_name|ljust:45 }}"
            "{{ submitter_agreement_number|default:''|ljust:14 }}"
            "{{ society_assigned_agreement_number|default:''|ljust:14 }}"
            "{{ cwr_code|default:code|ljust:9 }}01"
            "\r\n{% endautoescape %}"
        ),
    }
)

# CWR 3.x is kept as a fallback copy so imports do not fail. SADAIC export must use CWR 2.1/NWR.
TEMPLATES_30 = TEMPLATES_21.copy()
TEMPLATES_31 = TEMPLATES_30.copy()
