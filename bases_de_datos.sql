-- analitica_fondos.prorroga_periodo_de_gracia definition

CREATE TABLE `prorroga_periodo_de_gracia` (
  `id` int NOT NULL AUTO_INCREMENT,
  `docconvfondo` varchar(50) NOT NULL,
  `documento` varchar(50) NOT NULL,
  `convocatoria` varchar(6) NOT NULL,
  `fondo_sapiencia` varchar(10) NOT NULL,
  `fecha_fin_prorroga` date NOT NULL,
  `radicado_pqrs` varchar(100) NOT NULL,
  `responsable_registro` varchar(100) NOT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- analitica_fondos.renuncia_modalidad definition

CREATE TABLE `renuncia_modalidad` (
  `id` int NOT NULL AUTO_INCREMENT,
  `docconvfondo` varchar(50) NOT NULL,
  `documento` varchar(50) NOT NULL,
  `convocatoria` varchar(6) NOT NULL,
  `fondo_sapiencia` varchar(10) NOT NULL,
  `modalidad_a_la_cual_renuncia` varchar(100) NOT NULL,
  `radicado_pqrs` varchar(100) NOT NULL,
  `responsable_registro` varchar(100) NOT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;