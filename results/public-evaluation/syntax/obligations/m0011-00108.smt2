(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x106 (bvsle s_6 (_ bv15 4))))
(not $x106)))
(check-sat)
