(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x802 (bvsle s_3 (_ bv15 4))))
(not $x802)))
(check-sat)
