(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x380 (bvsle s_4 (_ bv0 4))))
(not $x380)))
(check-sat)
