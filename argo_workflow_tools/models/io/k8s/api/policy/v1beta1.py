# generated by datamodel-codegen:
#   filename:  https://raw.githubusercontent.com/argoproj/argo-workflows/master/api/openapi-spec/swagger.json
#   timestamp: 2021-11-13T19:15:49+00:00

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ...apimachinery.pkg.apis.meta import v1
from ...apimachinery.pkg.util import intstr


class PodDisruptionBudgetSpec(BaseModel):
    max_unavailable: Optional[intstr.IntOrString] = Field(
        None,
        alias="maxUnavailable",
        description='An eviction is allowed if at most "maxUnavailable" pods selected by "selector" are unavailable after the eviction, i.e. even in absence of the evicted pod. For example, one can prevent all voluntary evictions by specifying 0. This is a mutually exclusive setting with "minAvailable".',
    )
    min_available: Optional[intstr.IntOrString] = Field(
        None,
        alias="minAvailable",
        description='An eviction is allowed if at least "minAvailable" pods selected by "selector" will still be available after the eviction, i.e. even in the absence of the evicted pod.  So for example you can prevent all voluntary evictions by specifying "100%".',
    )
    selector: Optional[v1.LabelSelector] = Field(
        None,
        description="Label query over pods whose evictions are managed by the disruption budget.",
    )
