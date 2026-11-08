(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x212 (bvsle s_6 (_ bv15 4))))
(not $x212)))
(check-sat)
