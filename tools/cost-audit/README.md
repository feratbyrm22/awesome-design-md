# AWS Cost Audit (salt-okunur / read-only)

Boşta duran ve hâlâ fatura üreten AWS kaynaklarını bulur. **Hiçbir şeyi silmez, durdurmaz, değiştirmez.**
Her API çağrısı bir korumadan geçer: yalnızca `Describe* / List* / Get* / Lookup*` çağrılarına izin verilir,
diğer her çağrı istek gönderilmeden `WriteAttemptBlocked` hatasıyla engellenir.

## Kurulum ve çalıştırma

```bash
pip install boto3
python tools/cost-audit/cost_audit.py                          # tüm aktif bölgeler
python tools/cost-audit/cost_audit.py --regions eu-central-1 us-east-1
python tools/cost-audit/cost_audit.py --profile prod --json rapor.json --csv rapor.csv
```

Gereken IAM izni: AWS managed `ReadOnlyAccess` (veya `ViewOnlyAccess` + `cloudwatch:GetMetricStatistics`).

## Neleri yakalar

| Servis | Kontrol |
|---|---|
| EBS | Hiçbir sunucuya bağlı olmayan disk; gp2 → gp3 tasarrufu |
| EBS Snapshot | 90 günden eski, AMI'ye bağlı olmayan snapshot (kaynak disk silinmişse belirtilir) |
| Elastic IP | Hiçbir kaynağa bağlı olmayan IP |
| EC2 | Durdurulmuş sunucu (disk ücreti sürer); 14 günde ort. CPU < %5 ve tepe < %20 olan sunucu |
| NAT Gateway | 14 günde < 1 GiB trafik |
| ALB / NLB / CLB | Sağlıklı hedefi olmayan veya 14 günde 0 istek alan load balancer |
| RDS | Durdurulmuş DB; 14 günde 0 bağlantı; 90 günden eski manuel snapshot |
| CloudWatch Logs | Saklama süresi (retention) olmayan, ≥ 1 GB log grubu |

Eşikler parametreyle değişir: `--days`, `--cpu-threshold`, `--snapshot-days`, `--min-log-gb`.

## Önemli not: tutarlar tahmindir

Aylık $ değerleri us-east-1 on-demand liste fiyatlarına göre **yaklaşık** hesaplanır (`PRICES` tablosu).
Bölge farkı, Savings Plan / RI indirimi ve vergi dahil değildir. Bir şeyi silmeden önce gerçek tutarı
AWS Cost Explorer'dan doğrulayın. Snapshot'lar artımlı olduğu için gösterilen tutar üst sınırdır.

## Test

```bash
pip install "moto[ec2,rds,elbv2,cloudwatch,logs]" pytest
cd tools/cost-audit && python -m pytest -q
```
Testler sahte bir AWS (moto) üzerinde çalışır; gerçek hesaba dokunmaz.
