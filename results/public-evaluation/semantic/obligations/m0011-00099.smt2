(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x973 (bvsge s_6 (_ bv0 4))))
(not $x973)))
(check-sat)
