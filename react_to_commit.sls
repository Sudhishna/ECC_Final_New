Run interface sls:
  local.state.apply:
    - tgt: {{ data['hostname'] }}
    - arg:
      - jsnapy
