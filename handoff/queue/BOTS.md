# BOTS rung -- 2 open orders

## 3dc2832846bc  [MINOR]  STALLED_UNRESTARTABLE

- **where**: 
- **found_by**: foreman.kill_stalled_job
- **seen**: 13

stalled and deliberately NOT killed, because nothing would bring them back promptly: calibrate:40992

```
{
  "jobs": [
    "calibrate:40992"
  ]
}
```

## 2da53c3e192f  [MINOR]  HOST_QUARANTINED

- **where**: www.dandwiki.com
- **found_by**: binding_health
- **seen**: 8

www.dandwiki.com: host unreachable: siteinfo returned nothing usable -- the API is not answering (present probe: 8 known-present title(s) all returned nothing or too little to be a page (tried: 'Engineer', 'Gadgets', 'Energy', 'Signature Device'))

