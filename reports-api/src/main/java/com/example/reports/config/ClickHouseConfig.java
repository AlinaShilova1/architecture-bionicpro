package com.example.reports.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import ru.yandex.clickhouse.ClickHouseDataSource;

import javax.sql.DataSource;
import java.util.Properties;

@Configuration
public class ClickHouseConfig {

    @Value("${spring.datasource.clickhouse.url}")
    private String url;

    @Value("${spring.datasource.clickhouse.username:default}")
    private String username;

    @Value("${spring.datasource.clickhouse.password:}")
    private String password;

    @Bean
    public DataSource clickHouseDataSource() {
        Properties props = new Properties();
        props.setProperty("user", username);
        props.setProperty("password", password);
        return new ClickHouseDataSource(url, props);
    }

    @Bean
    public JdbcTemplate clickHouseJdbcTemplate(DataSource clickHouseDataSource) {
        return new JdbcTemplate(clickHouseDataSource);
    }
}