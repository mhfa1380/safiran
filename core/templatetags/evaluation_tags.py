from django import template

from core.evaluation_links import build_evaluation_url

register = template.Library()


@register.simple_tag
def evaluation_url(
    country="",
    major="",
    university="",
    ref="",
    target_degree="",
    intent="",
):
    return build_evaluation_url(
        country=country,
        major=major,
        university=university,
        ref=ref,
        target_degree=target_degree,
        intent=intent,
    )
