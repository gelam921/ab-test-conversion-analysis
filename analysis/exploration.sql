-- Question 1: Does the ad effect vary by day of week?
SELECT
    test_group,
    most_ads_day,
    count(*) AS total_users,
    sum(converted::int) AS conversions,
    round(100.0 * sum(converted::int) / count(*), 2) AS conversion_rate_pct
FROM ab_test
GROUP BY test_group, most_ads_day
ORDER BY test_group, conversion_rate_pct DESC;

-- Question 2: Dose-response — bucket ad-group users into exposure deciles
-- using NTILE, then compare conversion rate per bucket
WITH ad_group_deciles AS (
    SELECT
        converted,
        total_ads,
        NTILE(10) OVER (ORDER BY total_ads) AS ads_decile
    FROM ab_test
    WHERE test_group = 'ad'
)
SELECT
    ads_decile,
    count(*) AS users,
    min(total_ads) AS min_ads_in_decile,
    max(total_ads) AS max_ads_in_decile,
    round(100.0 * sum(converted::int) / count(*), 2) AS conversion_rate_pct
FROM ad_group_deciles
GROUP BY ads_decile
ORDER BY ads_decile;
