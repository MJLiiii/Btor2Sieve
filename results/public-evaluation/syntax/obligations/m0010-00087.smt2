(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x142 (= i_4 (_ bv2147483648 32))))
(not $x142)))
(check-sat)
