(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1613 (= i_6 (_ bv128 8))))
(not $x1613)))
(check-sat)
