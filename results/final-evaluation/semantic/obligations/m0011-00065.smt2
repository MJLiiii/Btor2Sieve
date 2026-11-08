(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x438 (bvsge i_2 (_ bv15 4))))
(not $x438)))
(check-sat)
